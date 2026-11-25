# -*- coding: utf-8 -*-
# Falcon networkResource list object
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import wx
import pywintypes

import background_wait
import misc
import network_resource
import browsableObjects
import globalVars
import errorCodes

from simpleDialog import dialog
from .base import *
from .constants import *


class NetworkResourceList(FalconListBase):
    """ネットワークリソースの一覧を扱うクラス。"""

    def __init__(self):
        super().__init__()
        self.supportedSorts = [SORT_TYPE_BASENAME]
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
        t = misc.Timer()
        if isinstance(
                path,
                list):  # パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
            self.resources += path
            return errorCodes.OK
        # end copy
        if not silent:
            globalVars.app.say(path[2:])

        # 共有フォルダの一覧の取得
        try:
            shares = network_resource.get_share_icons_with_auth(path, globalVars.app.main_window.GetHandle())
        except background_wait.Canceled:
            return errorCodes.CANCELED
        except pywintypes.error as er:
            self.log.error("Cannot get shares of %s: %s" % (path, er))
            if network_resource.is_cancelled_error(er):
                return errorCodes.ACCESS_DENIED
            if network_resource.is_connection_error(er.winerror):
                dialog(_("エラー"), network_resource.get_connection_error_message(path, er.strerror))
                return errorCodes.NETWORK_UNAVAILABLE
            dialog(
                _("エラー"),
                _("ネットワーク上のリソース一覧を取得できませんでした(%(error)s)") % {
                    "error": er.strerror})
            return errorCodes.ACCESS_DENIED

        # 取得に失敗した時に表示中の一覧が壊れないように、取得できてから入れ替える
        self.rootDirectory = path
        self.resources.clear()
        for share, icon in shares:
            s = browsableObjects.NetworkResource()
            s.Initialize(share[len(path) + 1:], share, "", icon)
            self.resources.append(s)
        self.ApplySort()

        self.log.debug(
            "Network resource list created in %d seconds." %
            t.elapsed)
        self.log.debug(str(len(self.resources)) + " resources found.")
        return errorCodes.OK
