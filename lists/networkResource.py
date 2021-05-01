# -*- coding: utf-8 -*-
# Falcon networkResource list object
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import wx
import win32wnet

import misc
import browsableObjects
import globalVars
import errorCodes

from simpleDialog import dialog
from .base import *
from .constants import *
from win32com.shell import shell, shellcon


class NetworkResourceList(FalconListBase):
    """ネットワークリソースの一覧を扱うクラス。"""

    def __init__(self):
        super().__init__()
        self.supportedSorts = []  # ソート不可
        self.columns = {
            _("名前"): wx.LIST_FORMAT_LEFT,
        }
        self.resources = []
        self.lists = [self.resources]

    def Update(self):
        return self.Initialize(self.rootDirectory, True)

    def Initialize(self, path, silent=False):
        """リソースの情報を取得し、リストを初期化する。"""
        self.log.debug("Getting resources list...")
        self.rootDirectory = path
        t = misc.Timer()
        if isinstance(
                path,
                list):  # パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
            self.resources += path
            return errorCodes.OK
        # end copy
        self.resources.clear()
        if not silent:
            globalVars.app.say(path[2:])

        # 取得対象を構造体にセット
        rootResource = win32wnet.NETRESOURCE()
        rootResource.lpRemoteName = path

        # リソースリストの取得
        try:
            h = win32wnet.WNetOpenEnum(2, 1, 0, rootResource)
            # 2=RESOURCE_GLOBALNET
            # 1=RESOURCETYPE_DISK
            lst = win32wnet.WNetEnumResource(h, 64)  # 65以上の指定不可
            win32wnet.WNetCloseEnum(h)
        except win32wnet.error as er:
            dialog(
                _("エラー"),
                _("ネットワーク上のリソース一覧を取得できませんでした(%(error)s)") % {
                    "error": str(er)})
            return errorCodes.ACCESS_DENIED

        for l in lst:
            ret, shfileinfo = shell.SHGetFileInfo(
                l.lpRemoteName, 0, shellcon.SHGFI_ICON)
            s = browsableObjects.NetworkResource()
            self.log.debug(
                "network resource found and check IP address:" + l.lpRemoteName[2:])
            s.Initialize(l.lpRemoteName[len(path) + 1:],
                         l.lpRemoteName, "", shfileinfo[0])
            self.resources.append(s)

        self.log.debug(
            "Network resource list created in %d seconds." %
            t.elapsed)
        self.log.debug(str(len(self.resources)) + " resources found.")
        return errorCodes.OK
