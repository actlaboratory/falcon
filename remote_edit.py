# -*- coding: utf-8 -*-
# Falcon remote edit
# Note: All comments except these top lines will be written in Japanese.

"""
FTP・SFTP のサーバー上のファイルを開いて編集したときに、変更をサーバーに書き戻すための処理です。

ファイルを開くときは一時フォルダにダウンロードして、そのファイルの更新日時と大きさを覚えておきます。
falcon のウィンドウに戻ってきたときに、変わったファイルがあれば、アップロードするかどうかを尋ねます
（尋ねるのは views/main.py）。メインスレッドから使います。

falcon の終了時には、サーバーと同じ内容のまま（変更していない、または変更をアップロードした）の一時ファイルを消します。
アップロードしなかった変更があるファイルは、失わないように残します。
"""

import logging
import os
import shutil
import tempfile

log = logging.getLogger("falcon.remote_edit")

# 開くためにダウンロードしたファイルを置くフォルダ（一時フォルダの中）
TEMP_DIRECTORY_NAME = "falcon_remote"


def get_temp_root():
    """開くためにダウンロードしたファイルを置くフォルダのパス"""
    return os.path.join(tempfile.gettempdir(), TEMP_DIRECTORY_NAME)


class EditedFile:
    """開いたファイル1つ"""

    def __init__(self, local_path, location, path):
        self.local_path = local_path
        # ファイルのあるフォルダ（remote_storage.Location）と、サーバー上のファイルのパス
        self.location = location
        self.path = path
        # 前に調べたときの状態（同じ変更について何度も尋ねないため）
        self.stamp = _get_stamp(local_path)
        # サーバーと同じ内容だったときの状態（ダウンロードしたとき、またはアップロードしたとき）
        self.synced_stamp = self.stamp

    def get_name(self):
        return self.path.rsplit("/", 1)[-1]

    def begin_upload(self):
        """アップロードを始める。アップロードする内容の状態を返す（終わったら finish_upload に渡す）"""
        return _get_stamp(self.local_path)

    def finish_upload(self, stamp):
        """アップロードが成功した。stamp は begin_upload の戻り値"""
        self.synced_stamp = stamp


def _get_stamp(path):
    """変更を調べるための、更新日時と大きさ。ファイルがなければ None"""
    try:
        info = os.stat(path)
    except OSError:
        return None
    return (info.st_mtime_ns, info.st_size)


class EditTracker:
    """開いたファイルの一覧"""

    def __init__(self):
        self._files = []

    def add(self, local_path, location, path):
        """開いたファイルを覚える"""
        self._files = [f for f in self._files if os.path.normcase(f.local_path) != os.path.normcase(local_path)]
        self._files.append(EditedFile(local_path, location, path))

    def pop_changed(self):
        """
        前に調べたときから変わったファイルのリストを返す。返したファイルは、今の状態を覚え直す
        （同じ変更について何度も尋ねないため）。消えたファイルは一覧から除く。
        """
        changed = []
        remaining = []
        for f in self._files:
            stamp = _get_stamp(f.local_path)
            if stamp is None:
                continue
            if stamp != f.stamp:
                f.stamp = stamp
                changed.append(f)
            remaining.append(f)
        self._files = remaining
        return changed

    def cleanup(self):
        """
        (終了時)サーバーと同じ内容の一時ファイルを、入っているフォルダごと消す。
        アップロードしていない変更があるファイルと、開いたままで消せないファイルは残す。
        """
        root = os.path.normcase(get_temp_root())
        for f in self._files:
            directory = os.path.dirname(f.local_path)
            # 念のため、一時フォルダの中の、ファイルごとに作ったフォルダだけを消す
            if os.path.normcase(os.path.dirname(directory)) != root:
                continue
            if _get_stamp(f.local_path) not in (f.synced_stamp, None):
                log.info("keep the edited file: %s" % f.local_path)
                continue
            try:
                shutil.rmtree(directory)
            except OSError as err:
                log.info("Cannot remove %s: %s" % (directory, err))
        self._files = []


edit_tracker = EditTracker()
