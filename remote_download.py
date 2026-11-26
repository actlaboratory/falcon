# -*- coding: utf-8 -*-
# Falcon remote download
# Note: All comments except these top lines will be written in Japanese.

"""
FTP・SFTP のサーバーからファイルとフォルダをダウンロードする処理です。
operation_manager.DownloadOperation から、別スレッドで実行します。
一覧の表示に使っている接続とは別に、ダウンロード用の接続を作ります。
"""

import logging
import os
import re
import threading

import remote_storage

log = logging.getLogger("falcon.remote_download")

# 同じ名前のファイル・フォルダがあるとき
CONFLICT_RENAME = "rename"
CONFLICT_SKIP = "skip"
CONFLICT_OVERWRITE = "overwrite"
CONFLICTS = (CONFLICT_RENAME, CONFLICT_SKIP, CONFLICT_OVERWRITE)

# Windows のファイル名に使えない文字
_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$", re.IGNORECASE)


class DownloadItem:
    """ダウンロードする項目"""

    def __init__(self, path, is_dir):
        # サーバー上のパス
        self.path = path
        self.is_dir = is_dir

    def get_name(self):
        return self.path.rstrip("/").rsplit("/", 1)[-1]


class DownloadRequest:
    """ダウンロードの内容"""

    def __init__(self, location, items, directory, conflict=CONFLICT_RENAME):
        # サーバー（remote_storage.Location）
        self.location = location
        # DownloadItem のリスト
        self.items = items
        # 保存先のフォルダ
        self.directory = directory
        self.conflict = conflict


def get_local_name(name):
    """サーバー上の名前を、Windows で使える名前にする。変える必要がなければそのまま返す"""
    result = _INVALID_CHARS.sub("_", name).rstrip(". ")
    if result == "":
        result = "_"
    if _RESERVED_NAMES.match(result):
        result = "_" + result
    return result


def make_unique_path(path):
    """同じ名前のファイル・フォルダがあれば、「名前 (2).txt」のように番号を付けたパスを返す"""
    if not os.path.lexists(path):
        return path
    directory, name = os.path.split(path)
    base, extension = os.path.splitext(name)
    number = 2
    while True:
        candidate = os.path.join(directory, "%s (%d)%s" % (base, number, extension))
        if not os.path.lexists(candidate):
            return candidate
        number += 1


class _File:
    """ダウンロードするファイル1つ"""

    def __init__(self, path, local_path, size):
        self.path = path
        self.local_path = local_path
        self.size = size


class DownloadJob:
    """ダウンロードを別スレッドで実行し、進み具合と結果を持つ"""

    def __init__(self, request):
        self._request = request
        self._cancel = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._client = None
        self.percentage = None
        # 利用者に知らせる注意（名前を変えて保存した項目など）の (対象, 内容) のリスト
        self.warnings = []
        # 失敗した項目の (対象, 内容) のリスト
        self.errors = []
        self.canceled = False

    def start(self):
        self._thread.start()

    def wait(self, seconds):
        self._thread.join(seconds)
        return self.is_finished()

    def is_finished(self):
        return not self._thread.is_alive()

    def cancel(self):
        """中止を指示する。実際に止まるのは少し後"""
        self._cancel.set()

    def _check_canceled(self, size=0):
        if self._cancel.is_set():
            raise remote_storage.Canceled()

    def _run(self):
        try:
            os.makedirs(self._request.directory, exist_ok=True)
            self._connect()
            files = self._plan()
            self._download(files)
        except remote_storage.Canceled:
            self.canceled = True
        except remote_storage.RemoteError as err:
            self.errors.append((self._request.location.get_url(), str(err)))
        except Exception as err:
            log.exception("download failed")
            self.errors.append((self._request.location.get_url(), str(err)))
        finally:
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass

    def _connect(self):
        location = self._request.location
        try:
            self._client = remote_storage.connect(location, remote_storage.credential_store.get(location))
        except (remote_storage.AuthRequired, remote_storage.UnknownHostKey, remote_storage.UntrustedCertificate) as err:
            # 一覧を開いたときに確認しているので、通常は起きない
            raise remote_storage.RemoteError(_("接続できませんでした。一覧を開き直してから、もう一度お試しください。\n(%(error)s)") % {"error": err})

    def _plan(self):
        """保存先を決め、ダウンロードするファイルの一覧を作る。フォルダはここで作る"""
        files = []
        for item in self._request.items:
            self._check_canceled()
            local_path = self._get_top_local_path(item)
            if local_path is None:
                continue
            try:
                if item.is_dir:
                    self._plan_folder(item.path, local_path, files)
                else:
                    entry = self._client.get_entry(item.path)
                    files.append(_File(item.path, local_path, entry.size))
            except remote_storage.ConnectError:
                raise
            except (remote_storage.RemoteError, OSError) as err:
                self.errors.append((item.path, str(err)))
        return files

    def _get_top_local_path(self, item):
        """選ばれた項目の保存先のパスを、同じ名前があるときの指定に従って決める。保存しない場合は None"""
        name = item.get_name()
        local_name = get_local_name(name)
        if local_name != name:
            self.warnings.append((item.path, _("Windows で使えない文字を含むため、「%(name)s」という名前で保存します。") % {"name": local_name}))
        local_path = os.path.join(self._request.directory, local_name)
        if not os.path.lexists(local_path):
            return local_path
        conflict = self._request.conflict
        if conflict == CONFLICT_SKIP:
            self.warnings.append((item.path, _("同じ名前の項目が保存先にあるため、保存しませんでした。")))
            return None
        if conflict == CONFLICT_RENAME:
            return make_unique_path(local_path)
        # 上書き。フォルダとファイルの種類が違う場合は上書きできない
        if item.is_dir != os.path.isdir(local_path):
            self.errors.append((item.path, _("保存先に、種類の違う同じ名前の項目があるため、上書きできません。")))
            return None
        return local_path

    def _plan_folder(self, path, local_path, files):
        """フォルダの中を順に調べ、フォルダを作ってファイルを files に加える"""
        os.makedirs(local_path, exist_ok=True)
        for entry in self._client.list_dir(path):
            self._check_canceled()
            child_path = remote_storage.join_path(path, entry.name)
            local_name = get_local_name(entry.name)
            if local_name != entry.name:
                self.warnings.append((child_path, _("Windows で使えない文字を含むため、「%(name)s」という名前で保存します。") % {"name": local_name}))
            child_local = os.path.join(local_path, local_name)
            if entry.is_dir:
                try:
                    self._plan_folder(child_path, child_local, files)
                except remote_storage.ConnectError:
                    raise
                except (remote_storage.RemoteError, OSError) as err:
                    self.errors.append((child_path, str(err)))
            elif os.path.isdir(child_local):
                self.errors.append((child_path, _("保存先に、同じ名前のフォルダがあるため、上書きできません。")))
            else:
                files.append(_File(child_path, child_local, entry.size))

    def _download(self, files):
        total = sum(max(f.size, 0) for f in files)
        done = [0]
        self.percentage = 0

        def on_progress(size):
            self._check_canceled()
            done[0] += size
            if total > 0:
                self.percentage = min(100, done[0] * 100 // total)

        for f in files:
            self._check_canceled()
            try:
                self._client.download(f.path, f.local_path, on_progress)
            except remote_storage.ConnectError as err:
                # 接続が切れた場合は、つなぎ直して続ける
                self.errors.append((f.path, str(err)))
                self._reconnect()
            except (remote_storage.RemoteError, OSError) as err:
                self.errors.append((f.path, str(err)))
        self.percentage = 100

    def _reconnect(self):
        try:
            self._client.close()
        except Exception:
            pass
        self._client = None
        self._connect()
