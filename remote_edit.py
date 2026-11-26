# -*- coding: utf-8 -*-
# Falcon remote edit
# Note: All comments except these top lines will be written in Japanese.

"""
FTP・SFTP のサーバー上のファイルを開いて編集したときに、変更をサーバーに書き戻すための処理です。

ファイルを開くときは一時フォルダにダウンロードして、そのファイルの更新日時と大きさを覚えておきます。
falcon のウィンドウに戻ってきたときに、変わったファイルがあれば、アップロードするかどうかを尋ねます
（尋ねるのは views/main.py）。メインスレッドから使います。
"""

import logging
import os

log = logging.getLogger("falcon.remote_edit")


class EditedFile:
    """開いたファイル1つ"""

    def __init__(self, local_path, location, path):
        self.local_path = local_path
        # ファイルのあるフォルダ（remote_storage.Location）と、サーバー上のファイルのパス
        self.location = location
        self.path = path
        self.stamp = _get_stamp(local_path)

    def get_name(self):
        return self.path.rsplit("/", 1)[-1]


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


edit_tracker = EditTracker()
