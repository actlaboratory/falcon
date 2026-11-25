# -*- coding: utf-8 -*-
# Falcon file list object
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2021 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import os
import wx
import win32file
import pywintypes
import background_wait
import constants
import misc
import network_resource
import browsableObjects
import globalVars
import errorCodes
from win32com.shell import shell, shellcon

from simpleDialog import *

from .fileListBase import *
from .constants import *


def _load(task, directory):
    """(別スレッド)ディレクトリの内容を調べ、フォルダのリストとファイルのリストを返す。"""
    is_remote = network_resource.is_remote_path(directory)
    cache = {}
    folders = []
    files = []
    for elem in win32file.FindFilesIterator(os.path.join(directory, "*")):
        task.check_canceled()
        name = elem[8]
        if name in (".", ".."):
            continue
        is_folder = bool(elem[0] & win32file.FILE_ATTRIBUTE_DIRECTORY)
        icon, type_string = _get_shell_info(os.path.join(directory, name), is_folder, is_remote, cache)
        item = browsableObjects.Folder() if is_folder else browsableObjects.File()
        size = -1 if is_folder else (elem[4] << 32) + elem[5]
        item.Initialize(directory, name, "", size, elem[3], elem[0], type_string, elem[1], elem[9], icon)
        if is_folder:
            folders.append(item)
        else:
            files.append(item)
    return folders, files


def _get_shell_info(fullpath, is_folder, is_remote, cache):
    """
    (別スレッド)アイコンと種類を返す。一度調べた拡張子のものは cache から返す。
    ネットワーク上では、1件ごとの通信を避けるため、実物を調べずに名前と属性だけから求める。
    """
    key = "/folder/" if is_folder else os.path.splitext(fullpath)[1]
    if key in cache:
        return cache[key]
    flags = shellcon.SHGFI_ICON | shellcon.SHGFI_TYPENAME
    attributes = 0
    if is_remote:
        flags |= shellcon.SHGFI_USEFILEATTRIBUTES
        attributes = win32file.FILE_ATTRIBUTE_DIRECTORY if is_folder else win32file.FILE_ATTRIBUTE_NORMAL
    dummy, info = shell.SHGetFileInfo(fullpath, attributes, flags)
    if key != "" or is_remote:
        cache[key] = (info[0], info[4])
    return info[0], info[4]


class FileList(FileListBase):
    """ファイルとフォルダの一覧を扱うリスト。"""

    def __init__(self):
        super().__init__()
        self.supportedSorts = [
            SORT_TYPE_BASENAME,
            SORT_TYPE_FILESIZE,
            SORT_TYPE_MODDATE,
            SORT_TYPE_ATTRIBUTES,
            SORT_TYPE_TYPESTRING]
        self.columns = {
            _("ファイル名"): wx.LIST_FORMAT_LEFT,
            _("サイズ"): wx.LIST_FORMAT_RIGHT,
            _("更新"): wx.LIST_FORMAT_LEFT,
            _("属性"): wx.LIST_FORMAT_LEFT,
            _("種類"): wx.LIST_FORMAT_LEFT
        }
        self.files = []
        self.folders = []
        self.lists = [self.folders, self.files]

    def Update(self):
        return self.Initialize(self.rootDirectory, True)

    def Initialize(self, dir, silent=False):
        """ディレクトリからファイル情報を取得し、リストを初期化する。入力は絶対パスでなければならない。情報が取得できなかった場合、errorCodes.OK以外が返る。silentがTrueなら読み上げは行われない。"""
        if isinstance(
                dir, list):  # パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
            self._copyFromList(dir)
            return errorCodes.OK
        # end copy
        dir_spl = dir[len(os.path.splitdrive(dir)[0]) + 1:].split("\\")
        level = len(dir_spl)
        if dir_spl[0] == "":
            level -= 1
        if not silent:
            r = []
            if globalVars.app.settings.get_bool("on_list_moved", "read_directory_level", True):
                drive = os.path.splitdrive(dir)[0]
                if len(drive) == 2:
                    drive = drive[0]
                if level == 0:
                    r.append(_("%sルート" % drive))
                else:
                    r.append(_("%(name)sの%(level)d ") % {"name": drive, "level": level})
            if globalVars.app.settings.get_bool("on_list_moved", "read_directory_name", True):
                r.append(dir_spl[level - 1])
            if len(r) > 0:
                globalVars.app.say(" ".join(r))
        # end read
        self.log.debug("Getting file list for %s..." % dir)
        t = misc.Timer()
        try:
            folders, files = background_wait.run(_load, dir)
        except background_wait.Canceled:
            return errorCodes.CANCELED
        except pywintypes.error as err:
            self.log.error("Cannot open the directory! {0}".format(err))
            if err.winerror == 5:
                return errorCodes.ACCESS_DENIED
            if network_resource.is_connection_error(err.winerror):
                dialog(_("エラー"), network_resource.get_connection_error_message(dir, err.strerror))
                return errorCodes.NETWORK_UNAVAILABLE
            dialog(
                _("エラー"),
                _("フォルダを開くことができませんでした(%(error)s)") % {
                    "error": str(err)})
            return errorCodes.FATAL
        # end except
        # 取得に失敗した時に表示中の一覧が壊れないように、取得できてから入れ替える
        self.rootDirectory = dir
        self.folders[:] = folders
        self.files[:] = files
        self.log.debug("File list created in %f seconds." % t.elapsed)
        self.log.debug(str(len(self.folders)) +
                       " directories and " +
                       str(len(self.files)) +
                       " files found.")
        if self.sortCursor != 0 or self.sortDescending != 0:
            self.log.debug("Triggering sorting")
            self.ApplySort()
        # end ソートが必要ならソート
        return errorCodes.OK

    def _copyFromList(self, lst):
        self.log.debug("Copying from file list...")
        for elem in lst:
            if isinstance(elem, browsableObjects.File):
                self.files.append(elem)
            elif isinstance(elem, browsableObjects.Folder):
                self.folders.append(elem)
            # end ファイルかフォルダか
        # end for
    # end _copyFromList

    def GetTopFileIndex(self):
        """先頭ファイルのインデックス番号を返す。"""
        if len(self.files) > 0:
            return len(self.folders)
        else:
            return -1

    def GetFolderFileNumber(self):
        return len(self.folders), len(self.files)
