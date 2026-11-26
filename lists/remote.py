# -*- coding: utf-8 -*-
# Falcon remote list object
# Note: All comments except these top lines will be written in Japanese.

"""FTP・SFTP のサーバー上のフォルダの中身の一覧"""

import datetime

import wx
import win32file
from win32com.shell import shell, shellcon

import background_wait
import browsableObjects
import errorCodes
import globalVars
import misc
import remote_connect
import remote_storage

from simpleDialog import dialog
from .base import FalconListBase
from .constants import SORT_TYPE_BASENAME, SORT_TYPE_FILESIZE, SORT_TYPE_MODDATE, SORT_TYPE_TYPESTRING

# 更新日時がわからない項目を並べ替えるときに使う日時
_UNKNOWN_DATE = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)


class RemoteList(FalconListBase):
    """FTP・SFTP のサーバー上のフォルダの中身を扱うクラス。"""

    def __init__(self):
        super().__init__()
        self.supportedSorts = [SORT_TYPE_BASENAME, SORT_TYPE_FILESIZE, SORT_TYPE_MODDATE, SORT_TYPE_TYPESTRING]
        self.columns = {
            _("ファイル名"): wx.LIST_FORMAT_LEFT,
            _("サイズ"): wx.LIST_FORMAT_RIGHT,
            _("更新"): wx.LIST_FORMAT_LEFT,
            _("種類"): wx.LIST_FORMAT_LEFT,
        }
        self.folders = []
        self.files = []
        self.lists = [self.folders, self.files]
        # 表示中の場所（remote_storage.Location）と、その URL
        self.location = None
        self.rootDirectory = ""

    def Update(self):
        return self.Initialize(self.rootDirectory, True)

    def Initialize(self, target, silent=False):
        """
        URL で指定したフォルダの中身を取得し、リストを初期化する。
        target が browsableObjects のリストなら、取得せずにその項目で初期化する（選択項目の受け渡し用）。
        """
        if isinstance(target, list):
            for elem in target:
                (self.folders if isinstance(elem, browsableObjects.RemoteFolder) else self.files).append(elem)
            return errorCodes.OK
        try:
            location = remote_storage.parse_url(target)
        except ValueError as err:
            dialog(_("エラー"), str(err))
            return errorCodes.INVALID_PARAMETER
        if not silent:
            globalVars.app.say(location.get_display_host())
        t = misc.Timer()
        try:
            path, entries = remote_connect.run(location, _load, location.path)
        except background_wait.Canceled:
            return errorCodes.CANCELED
        except remote_storage.RemoteError as err:
            self.log.error("Cannot list %s: %s" % (location.get_url(), err))
            dialog(_("エラー"), _("%(url)s を開けませんでした。\n%(error)s") % {"url": location.get_url(), "error": err})
            if isinstance(err, remote_storage.ConnectError):
                return errorCodes.NETWORK_UNAVAILABLE
            return errorCodes.ACCESS_DENIED

        # 取得に失敗したときに表示中の一覧が壊れないよう、取得できてから入れ替える
        self.location = location.child(path)
        self.rootDirectory = self.location.get_url()
        self.folders.clear()
        self.files.clear()
        for entry in entries:
            self._append(entry)
        self.ApplySort()
        self.log.debug("%d items found in %f seconds." % (len(self), t.elapsed))
        return errorCodes.OK

    def _append(self, entry):
        path = remote_storage.join_path(self.location.path, entry.name)
        if entry.is_dir:
            elem = browsableObjects.RemoteFolder()
            type_string, icon = _get_folder_type()
        else:
            elem = browsableObjects.RemoteFile()
            type_string, icon = _get_file_type(entry.name)
        elem.Initialize(self.location, path, entry.size, entry.modified, type_string, icon, entry.permissions, entry.is_link)
        (self.folders if entry.is_dir else self.files).append(elem)

    def _getSortFunction(self, attrib):
        if attrib == SORT_TYPE_MODDATE:
            return lambda x: x.modDate or _UNKNOWN_DATE
        return super()._getSortFunction(attrib)


def _load(client, path):
    """(別スレッド)パスが空ならログインしたときのフォルダにして、(パス, 中身) を返す"""
    if path == "":
        path = client.get_initial_path()
    return path, client.list_dir(path)


# 拡張子ごとの (種類, アイコン)。同じアイコンを何度も作らないように覚えておく
_file_types = {}


def _get_file_type(name):
    """ファイルの種類の名前とアイコンを、拡張子から求める。サーバーには問い合わせない"""
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension not in _file_types:
        dummy, info = shell.SHGetFileInfo(
            "dummy." + extension if extension else "dummy", win32file.FILE_ATTRIBUTE_NORMAL,
            shellcon.SHGFI_USEFILEATTRIBUTES | shellcon.SHGFI_TYPENAME | shellcon.SHGFI_ICON)
        _file_types[extension] = (info[4], info[0])
    return _file_types[extension]


def _get_folder_type():
    """フォルダの種類の名前とアイコン"""
    if None not in _file_types:
        dummy, info = shell.SHGetFileInfo(
            "dummy", win32file.FILE_ATTRIBUTE_DIRECTORY,
            shellcon.SHGFI_USEFILEATTRIBUTES | shellcon.SHGFI_TYPENAME | shellcon.SHGFI_ICON)
        _file_types[None] = (info[4], info[0])
    return _file_types[None]
