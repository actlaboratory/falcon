# -*- coding: utf-8 -*-
# Falcon remote transfer
# Note: All comments except these top lines will be written in Japanese.

"""
FTP・SFTP のサーバーとの間で、ファイルとフォルダを転送（ダウンロード・アップロード）したり、
サーバー上の項目を削除したりする処理です。
operation_manager の RemoteOperation から、別スレッドで実行します。
一覧の表示に使っている接続とは別に、転送用の接続を作ります。画面の部品には触りません。
"""

import datetime
import logging
import os
import re
import threading

import remote_storage

log = logging.getLogger("falcon.remote_transfer")

# 同じ名前のファイル・フォルダがあるとき
CONFLICT_RENAME = "rename"
CONFLICT_SKIP = "skip"
CONFLICT_OVERWRITE = "overwrite"
# 転送元のほうが新しい場合だけ上書きする
CONFLICT_NEWER = "newer"
# 転送先のファイルが転送元より小さい場合は、続きから転送する（途中で止まった転送の再開）
CONFLICT_RESUME = "resume"
CONFLICTS = (CONFLICT_RENAME, CONFLICT_SKIP, CONFLICT_OVERWRITE, CONFLICT_NEWER, CONFLICT_RESUME)

# Windows のファイル名に使えない文字
_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# フォルダをたどる深さの上限。シンボリックリンクがループしていて、実際のパスを調べられない場合に止めるため
MAX_DEPTH = 64
_RESERVED_NAMES = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\..*)?$", re.IGNORECASE)


def get_conflict_names():
    """CONFLICTS と同じ順の、同じ名前があるときの扱いの表示名"""
    return [
        _("別の名前にする"),
        _("転送しない"),
        _("上書きする"),
        _("転送元のほうが新しい場合だけ上書きする"),
        _("続きから転送する（転送先のほうが小さい場合）"),
    ]


class DownloadItem:
    """ダウンロードする項目"""

    def __init__(self, path, is_dir, is_link=False):
        # サーバー上のパス
        self.path = path
        self.is_dir = is_dir
        # シンボリックリンクかどうか（削除するときに、リンク先の中身を消さないため）
        self.is_link = is_link

    def get_name(self):
        return remote_storage.get_name(self.path)


class UploadItem:
    """アップロードする項目"""

    def __init__(self, local_path, name=None):
        self.local_path = local_path
        # サーバーに保存する名前。None ならローカルと同じ名前
        self.name = name or os.path.basename(local_path.rstrip("\\/"))

    def get_name(self):
        return self.name


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


class UploadRequest:
    """アップロードの内容"""

    def __init__(self, location, items, conflict=CONFLICT_RENAME):
        # アップロード先のフォルダ（remote_storage.Location。path がフォルダ）
        self.location = location
        # UploadItem のリスト
        self.items = items
        self.conflict = conflict


class DeleteRequest:
    """サーバー上の項目の削除の内容"""

    def __init__(self, location, items):
        # 削除する項目のあるフォルダ（remote_storage.Location）
        self.location = location
        # DownloadItem のリスト（パスとフォルダかどうか）
        self.items = items


def get_local_name(name):
    """サーバー上の名前を、Windows で使える名前にする。変える必要がなければそのまま返す"""
    result = _INVALID_CHARS.sub("_", name).rstrip(". ")
    if result == "":
        result = "_"
    if _RESERVED_NAMES.match(result):
        result = "_" + result
    return result


def _numbered_names(name):
    """「名前 (2).txt」「名前 (3).txt」… を順に返す"""
    base, extension = os.path.splitext(name)
    number = 2
    while True:
        yield "%s (%d)%s" % (base, number, extension)
        number += 1


def make_unique_path(path):
    """同じ名前のファイル・フォルダがあれば、「名前 (2).txt」のように番号を付けたパスを返す"""
    if not os.path.lexists(path):
        return path
    directory, name = os.path.split(path)
    for candidate in _numbered_names(name):
        candidate = os.path.join(directory, candidate)
        if not os.path.lexists(candidate):
            return candidate


def make_unique_name(name, existing):
    """existing（名前の集まり）にない名前を返す。name がなければそのまま"""
    if name not in existing:
        return name
    for candidate in _numbered_names(name):
        if candidate not in existing:
            return candidate


def decide(conflict, source_size, source_modified, destination_size, destination_modified, precision=1):
    """
    転送先に同じ名前のファイルがあるときに、どうするかを決める。
    戻り値は (転送するかどうか, 転送を始める位置)。CONFLICT_RENAME と CONFLICT_SKIP は呼び出し側で扱う。
    """
    if conflict == CONFLICT_NEWER:
        if source_modified is None or destination_modified is None:
            # 比べられない場合は、転送しておく
            return True, 0
        tolerance = datetime.timedelta(seconds=max(precision, 1))
        return source_modified - destination_modified >= tolerance, 0
    if conflict == CONFLICT_RESUME:
        if source_size < 0 or destination_size < 0 or destination_size > source_size:
            return True, 0
        if destination_size == source_size:
            return False, 0
        return True, destination_size
    return True, 0


def mark_from_internet(local_path, url):
    """
    ダウンロードしたファイルに、インターネットから来たことを表す印（Zone.Identifier）を付ける。
    Windows の SmartScreen や Office の保護ビューが、ブラウザーでダウンロードしたファイルと同じように働く。
    印を付けられないドライブ（FAT など）では何もしない。url にはユーザー名を含めないこと。
    """
    try:
        with open(local_path + ":Zone.Identifier", "w", encoding="utf-8") as f:
            f.write("[ZoneTransfer]\r\nZoneId=3\r\nHostUrl=%s\r\n" % url)
    except OSError as err:
        log.debug("Cannot mark %s: %s" % (local_path, err))


def _get_local_modified(path):
    try:
        return datetime.datetime.fromtimestamp(os.stat(path).st_mtime, datetime.timezone.utc)
    except (OSError, ValueError, OverflowError):
        return None


class _File:
    """転送するファイル1つ"""

    def __init__(self, source, destination, size, offset=0, modified=None):
        # ダウンロードではサーバー上のパスとローカルのパス、アップロードではその逆
        self.source = source
        self.destination = destination
        self.size = size
        self.offset = offset
        # 転送元の更新日時。転送後に転送先へ設定する
        self.modified = modified


class RemoteJob:
    """サーバーへの操作を別スレッドで実行し、進み具合と結果を持つ。操作ごとに派生クラスを作る"""

    def __init__(self, location):
        self._location = location
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
            self._prepare()
            self._connect()
            self._execute()
        except remote_storage.Canceled:
            self.canceled = True
        except remote_storage.RemoteError as err:
            self.errors.append((self._location.get_url(), str(err)))
        except OSError as err:
            self.errors.append((self._location.get_url(), err.strerror or str(err)))
        except Exception as err:
            log.exception("remote operation failed")
            self.errors.append((self._location.get_url(), str(err)))
        finally:
            if self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass

    def _prepare(self):
        """接続する前の準備"""

    def _execute(self):
        raise NotImplementedError

    def _connect(self):
        location = self._location
        try:
            self._client = remote_storage.connect(location, remote_storage.credential_store.get(location))
        except (remote_storage.AuthRequired, remote_storage.UnknownHostKey, remote_storage.UntrustedCertificate) as err:
            # 一覧を開いたときに確認しているので、通常は起きない
            raise remote_storage.RemoteError(_("接続できませんでした。一覧を開き直してから、もう一度お試しください。\n(%(error)s)") % {"error": err})

    def _reconnect(self):
        try:
            self._client.close()
        except Exception:
            pass
        self._client = None
        self._connect()


class TransferJob(RemoteJob):
    """ダウンロードとアップロードに共通の処理"""

    def __init__(self, location, conflict):
        super().__init__(location)
        self._conflict = conflict
        # 転送先のほうが新しい・同じ大きさなどの理由で、転送しなかったファイルの数
        self._skipped = 0

    def _execute(self):
        files = self._plan()
        self._transfer(files)
        if self._skipped:
            self.warnings.append((self._get_destination_name(), _(
                "転送先に同じ名前の新しいファイル、または同じ大きさのファイルがあったため、%(count)d件は転送しませんでした。") % {"count": self._skipped}))

    def _plan(self):
        """転送するファイルの一覧を作る。転送先のフォルダはここで作る"""
        raise NotImplementedError

    def _get_destination_name(self):
        raise NotImplementedError

    def _transfer_file(self, f, on_progress):
        raise NotImplementedError

    def _set_modified(self, f):
        """転送先の更新日時を、転送元に合わせる。できなくてもエラーにしない"""
        raise NotImplementedError

    def _decide_file(self, source_size, source_modified, destination_size, destination_modified, precision=1):
        """転送先に同じ名前のファイルがある場合に、転送するかどうかと始める位置を決める"""
        transfer, offset = decide(self._conflict, source_size, source_modified, destination_size, destination_modified, precision)
        if not transfer:
            self._skipped += 1
        return transfer, offset

    def _transfer(self, files):
        total = sum(max(f.size - f.offset, 0) for f in files)
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
                self._transfer_file(f, on_progress)
            except remote_storage.ConnectError as err:
                # 接続が切れた場合は、つなぎ直して続ける
                self.errors.append((f.source, str(err)))
                self._reconnect()
                continue
            except (remote_storage.RemoteError, OSError) as err:
                self.errors.append((f.source, getattr(err, "strerror", None) or str(err)))
                continue
            if f.modified is not None:
                try:
                    self._set_modified(f)
                except remote_storage.ConnectError:
                    self._reconnect()
                except (remote_storage.RemoteError, OSError, ValueError, OverflowError) as err:
                    log.info("Cannot set the modified time of %s: %s" % (f.destination, err))
        self.percentage = 100


class DownloadJob(TransferJob):
    """ダウンロード"""

    def __init__(self, request):
        super().__init__(request.location, request.conflict)
        self._request = request
        # この操作で保存するパス（normcase）。サーバー上では違う名前が、Windows では同じ名前になる場合に区別する
        self._planned = set()

    def _prepare(self):
        os.makedirs(self._request.directory, exist_ok=True)

    def _reserve(self, path, source):
        """
        この操作の中で、ほかの項目と同じ保存先にならないようにしたパスを返す
        （「a:b」と「a_b」は、どちらも「a_b」になるため）。
        """
        if os.path.normcase(path) in self._planned:
            directory, name = os.path.split(path)
            for candidate in _numbered_names(name):
                candidate_path = os.path.join(directory, candidate)
                if os.path.normcase(candidate_path) not in self._planned and not os.path.lexists(candidate_path):
                    self.warnings.append((source, _("ほかの項目と同じ名前になるため、「%(name)s」という名前で保存します。") % {"name": candidate}))
                    path = candidate_path
                    break
        self._planned.add(os.path.normcase(path))
        return path

    def _get_destination_name(self):
        return self._request.directory

    def _plan(self):
        files = []
        for item in self._request.items:
            self._check_canceled()
            try:
                local_path, merge = self._get_top_local_path(item)
                if local_path is None:
                    continue
                local_path = self._reserve(local_path, item.path)
                if item.is_dir:
                    real = self._client.get_real_path(item.path)
                    self._plan_folder(item.path, local_path, files, {real} if real else set(), real, 0)
                else:
                    entry = self._client.get_entry(item.path)
                    self._add_file(item.path, entry, local_path, files, merge)
            except remote_storage.ConnectError:
                raise
            except (remote_storage.RemoteError, OSError) as err:
                self.errors.append((item.path, getattr(err, "strerror", None) or str(err)))
        return files

    def _get_top_local_path(self, item):
        """
        選ばれた項目の保存先のパスを、同じ名前があるときの指定に従って決める。
        (パス, 既にある項目に上書き・追加するかどうか) を返す。保存しない場合はパスが None
        """
        name = item.get_name()
        local_name = get_local_name(name)
        if local_name != name:
            self.warnings.append((item.path, _("Windows で使えない文字を含むため、「%(name)s」という名前で保存します。") % {"name": local_name}))
        local_path = os.path.join(self._request.directory, local_name)
        if not os.path.lexists(local_path):
            return local_path, False
        conflict = self._conflict
        if conflict == CONFLICT_SKIP:
            self.warnings.append((item.path, _("同じ名前の項目が保存先にあるため、保存しませんでした。")))
            return None, False
        if conflict == CONFLICT_RENAME:
            return make_unique_path(local_path), False
        # フォルダとファイルの種類が違う場合は上書きできない
        if item.is_dir != os.path.isdir(local_path):
            self.errors.append((item.path, _("保存先に、種類の違う同じ名前の項目があるため、上書きできません。")))
            return None, False
        return local_path, True

    def _add_file(self, path, entry, local_path, files, merge):
        """ダウンロードするファイルを files に加える。保存先に同じ名前のファイルがあれば、指定に従う"""
        offset = 0
        if merge and os.path.isfile(local_path):
            transfer, offset = self._decide_file(
                entry.size, entry.modified, os.path.getsize(local_path), _get_local_modified(local_path), entry.precision)
            if not transfer:
                return
        files.append(_File(path, local_path, entry.size, offset, entry.modified))

    def _plan_folder(self, path, local_path, files, ancestors, real, depth):
        """
        フォルダの中を順に調べ、フォルダを作ってファイルを files に加える。
        ancestors はたどってきたフォルダの実際のパス、real はこのフォルダの実際のパス（わからなければ None）。
        リンクの先がたどってきたフォルダならループなので、たどらない。
        実際のパスを調べられないサーバー（FTP）では、深さの上限で止める。
        """
        if depth >= MAX_DEPTH:
            self.errors.append((path, _("フォルダが深すぎるため、これより下はダウンロードしませんでした。シンボリックリンクがループしている可能性があります。")))
            return
        os.makedirs(local_path, exist_ok=True)
        for entry in self._client.list_dir(path):
            self._check_canceled()
            child_path = remote_storage.join_path(path, entry.name)
            local_name = get_local_name(entry.name)
            if local_name != entry.name:
                self.warnings.append((child_path, _("Windows で使えない文字を含むため、「%(name)s」という名前で保存します。") % {"name": local_name}))
            child_local = self._reserve(os.path.join(local_path, local_name), child_path)
            if entry.is_dir:
                if entry.is_link:
                    # リンクだけはサーバーに実際のパスを尋ねる。それ以外は親の実際のパスから求める
                    child_real = self._client.get_real_path(child_path)
                    if child_real is not None and child_real in ancestors:
                        self.warnings.append((child_path, _("シンボリックリンクが、たどってきたフォルダを指しているため（ループ）、中身はダウンロードしませんでした。")))
                        continue
                else:
                    child_real = remote_storage.join_path(real, entry.name) if real else None
                child_ancestors = ancestors | {child_real} if child_real else ancestors
                try:
                    self._plan_folder(child_path, child_local, files, child_ancestors, child_real, depth + 1)
                except remote_storage.ConnectError:
                    raise
                except (remote_storage.RemoteError, OSError) as err:
                    self.errors.append((child_path, getattr(err, "strerror", None) or str(err)))
            elif os.path.isdir(child_local):
                self.errors.append((child_path, _("保存先に、同じ名前のフォルダがあるため、上書きできません。")))
            else:
                self._add_file(child_path, entry, child_local, files, True)

    def _transfer_file(self, f, on_progress):
        self._client.download(f.source, f.destination, on_progress, f.offset)
        mark_from_internet(f.destination, self._location.get_url(f.source, with_user=False))

    def _set_modified(self, f):
        timestamp = f.modified.timestamp()
        os.utime(f.destination, (timestamp, timestamp))


class UploadJob(TransferJob):
    """アップロード"""

    def __init__(self, request):
        super().__init__(request.location, request.conflict)
        self._request = request

    def _get_destination_name(self):
        return self._request.location.get_url()

    def _plan(self):
        directory = self._request.location.path
        # アップロード先のフォルダがなければ作る
        self._client.make_dirs(directory)
        existing = {entry.name: entry for entry in self._client.list_dir(directory)}
        files = []
        for item in self._request.items:
            self._check_canceled()
            try:
                self._plan_top(item, directory, existing, files)
            except remote_storage.ConnectError:
                raise
            except (remote_storage.RemoteError, OSError) as err:
                self.errors.append((item.local_path, getattr(err, "strerror", None) or str(err)))
        return files

    def _plan_top(self, item, directory, existing, files):
        """選ばれた項目の、アップロード先の名前を同じ名前があるときの指定に従って決め、files に加える"""
        name = item.get_name()
        is_dir = os.path.isdir(item.local_path)
        if not is_dir and not os.path.isfile(item.local_path):
            self.errors.append((item.local_path, _("見つかりません。")))
            return
        entry = existing.get(name)
        if entry is not None:
            if self._conflict == CONFLICT_SKIP:
                self.warnings.append((item.local_path, _("同じ名前の項目がアップロード先にあるため、アップロードしませんでした。")))
                return
            if self._conflict == CONFLICT_RENAME:
                name = make_unique_name(name, existing)
                entry = None
            elif entry.is_dir != is_dir:
                self.errors.append((item.local_path, _("アップロード先に、種類の違う同じ名前の項目があるため、上書きできません。")))
                return
        # 同じ操作の中で、同じ名前を2回使わないようにする
        existing.setdefault(name, remote_storage.Entry(name, is_dir))
        path = remote_storage.join_path(directory, name)
        if is_dir:
            self._plan_folder(item.local_path, path, files, entry is not None, {_real_path(item.local_path)}, 0)
        else:
            self._add_file(item.local_path, path, entry, files)

    def _add_file(self, local_path, path, entry, files):
        """アップロードするファイルを files に加える。アップロード先に同じ名前のファイルがあれば、指定に従う"""
        size = os.path.getsize(local_path)
        modified = _get_local_modified(local_path)
        offset = 0
        if entry is not None and not entry.is_dir:
            transfer, offset = self._decide_file(size, modified, entry.size, entry.modified, entry.precision)
            if not transfer:
                return
        files.append(_File(local_path, path, size, offset, modified))

    def _plan_folder(self, local_path, path, files, merge, ancestors, depth):
        """
        フォルダの中を順に調べ、サーバーにフォルダを作ってファイルを files に加える。
        ancestors はたどってきたフォルダの実際のパス。ジャンクションやシンボリックリンクがその中を指していれば、たどらない。
        """
        if depth >= MAX_DEPTH:
            self.errors.append((local_path, _("フォルダが深すぎるため、これより下はアップロードしませんでした。")))
            return
        if merge:
            existing = {entry.name: entry for entry in self._client.list_dir(path)}
        else:
            self._client.make_dir(path)
            existing = {}
        with os.scandir(local_path) as it:
            children = sorted(it, key=lambda e: e.name)
        for child in children:
            self._check_canceled()
            child_path = remote_storage.join_path(path, child.name)
            entry = existing.get(child.name)
            try:
                if child.is_dir():
                    if entry is not None and not entry.is_dir:
                        self.errors.append((child.path, _("アップロード先に、同じ名前のファイルがあるため、上書きできません。")))
                        continue
                    real = _real_path(child.path)
                    if real in ancestors:
                        self.warnings.append((child.path, _("ジャンクションまたはシンボリックリンクが、たどってきたフォルダを指しているため（ループ）、中身はアップロードしませんでした。")))
                        continue
                    self._plan_folder(child.path, child_path, files, entry is not None, ancestors | {real}, depth + 1)
                elif child.is_file():
                    if entry is not None and entry.is_dir:
                        self.errors.append((child.path, _("アップロード先に、同じ名前のフォルダがあるため、上書きできません。")))
                        continue
                    self._add_file(child.path, child_path, entry, files)
            except remote_storage.ConnectError:
                raise
            except (remote_storage.RemoteError, OSError) as err:
                self.errors.append((child.path, getattr(err, "strerror", None) or str(err)))

    def _transfer_file(self, f, on_progress):
        self._client.upload(f.source, f.destination, on_progress, f.offset)

    def _set_modified(self, f):
        self._client.set_modified(f.destination, f.modified)


def _real_path(path):
    """ローカルのフォルダの、リンクをたどった実際のパス（大文字・小文字をそろえたもの）"""
    return os.path.normcase(os.path.realpath(path))


class DeleteJob(RemoteJob):
    """サーバー上のファイル・フォルダの削除。フォルダは中身も削除する"""

    def __init__(self, request):
        super().__init__(request.location)
        self._request = request
        # 削除できた項目のパス
        self.deleted = []

    def _execute(self):
        items = self._request.items
        self.percentage = 0
        for index, item in enumerate(items):
            self._check_canceled()
            try:
                if item.is_dir and not item.is_link:
                    self._remove_folder(item.path)
                else:
                    self._client.remove_file(item.path)
                self.deleted.append(item.path)
            except remote_storage.ConnectError as err:
                self.errors.append((item.path, str(err)))
                self._reconnect()
            except remote_storage.RemoteError as err:
                self.errors.append((item.path, str(err)))
            self.percentage = (index + 1) * 100 // len(items)

    def _remove_folder(self, path):
        """フォルダの中身を消してから、フォルダを消す"""
        for entry in self._client.list_dir(path):
            self._check_canceled()
            child = remote_storage.join_path(path, entry.name)
            # シンボリックリンクは、リンク先ではなくリンクそのものを消す
            if entry.is_dir and not entry.is_link:
                self._remove_folder(child)
            else:
                self._client.remove_file(child)
        self._client.remove_dir(path)
