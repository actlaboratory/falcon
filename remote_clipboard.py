# -*- coding: utf-8 -*-
# Falcon remote clipboard
# Note: All comments except these top lines will be written in Japanese.

"""
FTP・SFTP のサーバー上の項目の「コピー」「切り取り」を覚えておく処理です。

サーバー上の項目は Windows のクリップボードにファイルとして入れられないので、falcon の中で覚えておき、
クリップボードには URL を文字列として入れます。その後にほかのアプリなどでクリップボードが変わった場合は、
覚えている内容を使いません（クリップボードの更新番号で調べます）。メインスレッドから使います。
"""

import logging

import win32clipboard

import clipboard
import clipboardHelper

log = logging.getLogger("falcon.remote_clipboard")


class RemoteClipboardData:
    """コピー・切り取りした内容"""

    def __init__(self, location, items, operation):
        # 項目のあるフォルダ（remote_storage.Location）
        self.location = location
        # remote_transfer.DownloadItem のリスト
        self.items = items
        # clipboard.COPY または clipboard.MOVE
        self.operation = operation

    def is_move(self):
        return self.operation == clipboard.MOVE


class RemoteClipboard:
    """サーバー上の項目のコピー・切り取りを覚える"""

    def __init__(self):
        self._data = None
        self._sequence = None

    def set(self, location, items, operation=clipboard.COPY):
        """項目を覚え、クリップボードに URL を入れる"""
        text = "\n".join(location.get_url(item.path) for item in items)
        with clipboardHelper.Clipboard() as c:
            c.set_unicode_text(text)
        self._data = RemoteClipboardData(location, items, operation)
        self._sequence = win32clipboard.GetClipboardSequenceNumber()

    def get(self):
        """覚えている内容を返す。その後にクリップボードが変わっていれば None"""
        if self._data is None:
            return None
        if win32clipboard.GetClipboardSequenceNumber() != self._sequence:
            self.clear()
            return None
        return self._data

    def clear(self):
        self._data = None
        self._sequence = None


remote_clipboard = RemoteClipboard()
