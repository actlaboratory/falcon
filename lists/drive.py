# -*- coding: utf-8 -*-
# Falcon drive list object
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import wx
import win32api
import win32file
import win32wnet

import pywintypes
import constants
import misc
import browsableObjects
import globalVars
import errorCodes
import network_place

from simpleDialog import dialog
from .base import *
from .constants import *
from win32com.shell import shell, shellcon


class DriveList(FalconListBase):
    """ドライブの一覧を扱うクラス。"""

    def __init__(self):
        super().__init__()
        self.supportedSorts = [
            SORT_TYPE_BASENAME,
            SORT_TYPE_DRIVELETTER,
            SORT_TYPE_FREESPACE,
            SORT_TYPE_TOTALSPACE,
            SORT_TYPE_TYPESTRING]
        self.columns = {
            _("ラベル"): wx.LIST_FORMAT_LEFT,
            _("レター"): wx.LIST_FORMAT_LEFT,
            _("空き"): wx.LIST_FORMAT_RIGHT,
            _("合計"): wx.LIST_FORMAT_RIGHT,
            _("種類"): wx.LIST_FORMAT_LEFT
        }
        self.drives = []
        self.unusableDrives = []
        self.networkResources = []
        self.lists = [self.drives, self.unusableDrives, self.networkResources]

    def Update(self):
        return self.Initialize(None, True)

    def Initialize(self, lst=None, silent=False):
        """ドライブ情報を取得し、リストを初期化する。"""
        self.log.debug("Getting drives list...")
        self.rootDirectory = ""
        t = misc.Timer()
        if isinstance(
                lst, list):  # パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
            self._copyFromList(lst)
            return errorCodes.OK
        # end copy
        self.drives.clear()
        self.unusableDrives.clear()
        self.networkResources.clear()
        if not silent:
            globalVars.app.say(_("ドライブ洗濯"))
        drv = win32api.GetLogicalDrives()
        check = 1
        for i in range(26):
            if drv & check:
                self.Append(i)  # ドライブ検出
            check <<= 1
        # end ドライブ25個分調べる
        self._append_network_places()
        # ネットワーク上のコンピューターの追加はタブ側から来ることになった
        self.log.debug("Drives list created in %d seconds." % t.elapsed)
        self.log.debug("%d drives and %d unusableDrives found." %
                       (len(self.drives), len(self.unusableDrives)))
        self.log.debug("Triggering sorting")
        self.ApplySort()
        return errorCodes.OK

    def _copyFromList(self, lst):
        self.log.debug("Copying from list...")
        for elem in lst:
            if isinstance(elem, browsableObjects.NetworkResource):
                self.networkResources.append(elem)
            elif _is_listed_as_usable(elem):
                self.drives.append(elem)
            else:
                self.unusableDrives.append(elem)
            # end ファイルかフォルダか
        # end for
    # end _copyFromList

    def _append_network_places(self):
        """ネットワークの場所を一覧に加える。リンク先には接続しない。"""
        for place in network_place.get_places():
            # リンク先に接続せずにアイコンを得るため、ファイルの属性だけからアイコンを決める
            dummy, info = shell.SHGetFileInfo(
                place.folder, win32file.FILE_ATTRIBUTE_DIRECTORY, shellcon.SHGFI_ICON | shellcon.SHGFI_USEFILEATTRIBUTES)
            elem = browsableObjects.NetworkPlace()
            elem.initialize_place(place.name, place.target, place.folder, info[0])
            self.networkResources.append(elem)

    def AppendNetworkResource(self, resource):
        self.networkResources.append(resource)

    def Append(self, index):
        # ネットワークドライブは、接続できないと容量の取得に数十秒かかることがあるため、ここでは調べない
        d = GetDriveObject(index, load_remote_info=False)
        if _is_listed_as_usable(d):
            self.drives.append(d)
        else:
            self.unusableDrives.append(d)
        # end どっちに追加するか？

    def GetPendingDrives(self):
        """容量をまだ取得していないネットワークドライブの一覧を返す。"""
        return [d for d in self.drives if d.info_pending]

    def get_pending_disc_drives(self):
        """種類をまだ調べていない光学ドライブの一覧を返す。ディスクが入っていないドライブも含む。"""
        return [d for d in self.drives + self.unusableDrives if d.disc_type_pending]


def _is_listed_as_usable(drive):
    """ドライブを、使用可能なドライブとして一覧の前側に並べるかどうか。ネットワークドライブは接続できるか分からないので前側に並べる。"""
    return drive.total >= 0 or drive.type == win32file.DRIVE_REMOTE


def _get_remote_path(letter):
    """ネットワークドライブの接続先(\\\\server\\share)を返す。接続を確認しないので、すぐに返る。"""
    try:
        return win32wnet.WNetGetConnection(letter + ":")
    except pywintypes.error:
        return ""


def GetDriveObject(index, load_remote_info=True):
    """
        ドライブ情報を調べて、browsableObjectsで返す。Aドライブが0、Zドライブが25。
        load_remote_info=False の場合、ネットワークドライブの容量は調べず、info_pending=True のオブジェクトを返す。
    """
    letter = chr(index + 65)
    path = letter + ":\\"
    type = win32file.GetDriveType(path)
    if type == win32file.DRIVE_REMOTE and not load_remote_info:
        d = browsableObjects.Drive()
        remote_path = _get_remote_path(letter)
        d.Initialize(letter, -1, -1, type, remote_path, -1)
        d.remote_path = remote_path
        d.info_pending = True
        return d
    f = -1
    t = -1
    n = ""
    try:
        volumeInfo = win32api.GetVolumeInformation(path)
        n = volumeInfo[0]
        freeSpace = win32api.GetDiskFreeSpaceEx(path)
        f = freeSpace[0]
        t = freeSpace[1]
    except pywintypes.error as err:
        pass
    # エラーは無視
    d = browsableObjects.Drive()
    if type != win32file.DRIVE_REMOTE or t != -1:
        ret, shfileinfo = shell.SHGetFileInfo(
            letter + ":\\", 0, shellcon.SHGFI_ICON)
        d.Initialize(letter, f, t, type, n, shfileinfo[0])
    else:
        d.Initialize(letter, f, t, type, n, -1)
    return d
