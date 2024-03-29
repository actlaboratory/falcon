﻿# -*- coding: utf-8 -*-
# Falcon tab creator / navigator
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
なにもない状態からパス指定でタブを作ったり、既存のタブを指定してフォルダ移動したりできます。
"""

import ctypes
import logging
import os
import sys
import wx
import errorCodes
import lists
import globalVars
import constants
import misc
import views.ViewCreator
from . import fileList, driveList, streamList, searchResult, grepResult, NetworkResourceList, pastProgress
from simpleDialog import dialog

log = logging.getLogger("falcon.navigator")


def Navigate(
        target,
        cursor="",
        previous_tab=None,
        create_new_tab_info=None,
        environment=None):
    """
            指定したパスにアクセスする。現在のタブと違う種類のタブが必要とされた場合に、新しいタブを返す。今のタブを再利用した場合は、Trueを返す。失敗時にはエラーコードを返す。
            パスに空の文字を指定すると、ドライブリストへ行く。
            パスに辞書を指定した場合、内容によって動作が変わる。事前に取得したファイルリストからの検索などができる。
            create_new_tab_info に (parent,hPanel) のタプルがあれば、この情報を使って新規タブを作成する。これは、メインビューで使っている
    """
    if previous_tab is None and create_new_tab_info is None:
        return errorCodes.INVALID_PARAMETER
    parent = previous_tab.parent if previous_tab is not None else create_new_tab_info[0]
    hListCtrl = previous_tab.hListCtrl if previous_tab is not None else None
    creator = create_new_tab_info[1] if create_new_tab_info is not None else None
    targetItemIndex = -1
    if environment is None:
        environment = {}

    if isinstance(target, dict):
        if target['action'] == 'search':
            newtab = searchResult.SearchResultTab(environment)
            newtab.Initialize(parent, creator)
            newtab.StartSearch(
                target['basePath'],
                target['out_lst'],
                target['keyword'],
                target['isRegularExpression'])
        # end 検索
        if target['action'] == 'grep':
            newtab = grepResult.GrepResultTab({})
            newtab.Initialize(parent, creator)
            newtab.StartSearch(
                target['basePath'],
                target['out_lst'],
                target['keyword'],
                target['isRegularExpression'])
        # end grep検索
        if target['action'] == 'past':
            newtab = pastProgress.PastProgressTab(environment)
            newtab.Initialize(parent, creator)
            lst = lists.PastProgressList()
            lst.Initialize(
                header_directory=target["operator"].instructions["to"])
            newtab.Update(lst)
            newtab.SetFileOperator(target["operator"])
        # end 貼り付け
        # かならずviews.Main.Navigateを経由して呼び出されているはず
        return newtab
    # end targetが辞書の時の特殊処理

    target = os.path.expandvars(target)
    if target == "":  # ドライブリスト
        lst = lists.DriveList()
        lst.Initialize()
        if isinstance(previous_tab, driveList.DriveListTab):  # 再利用
            newtab = previous_tab
        else:
            newtab = driveList.DriveListTab(environment)
            newtab.Initialize(parent, creator, hListCtrl)
        # end 再利用するかどうか
        targetItemIndex = lst.Search(cursor, 1)
        if targetItemIndex == -1 and cursor != "":  # ネットワークドライブ対策
            targetItemIndex = lst.Search(cursor, 0)
    # end ドライブリストへ行く
    elif target[0:2] == "\\\\" and "\\" not in target[2:]:
        lst = lists.NetworkResourceList()
        result = lst.Initialize(target)
        if result != errorCodes.OK:
            return result  # アクセス不可
        newtab = NetworkResourceList.NetworkResourceListTab(environment)
        newtab.Initialize(parent, creator, hListCtrl)
    elif not os.path.exists(target):
        log.error("navigate failed: %s not exist." % target)
        dialog(_("エラー"), _("移動に失敗しました。移動先が存在しません。"))
        return errorCodes.FILE_NOT_FOUND
    elif os.path.isfile(target):  # 副ストリームへ移動
        lst = lists.StreamList()
        lst.Initialize(target)
        if isinstance(previous_tab, streamList.StreamListTab):  # 再利用
            newtab = previous_tab
        else:
            newtab = streamList.StreamListTab(environment)
            newtab.Initialize(parent, creator, hListCtrl)
        # end 再利用するかどうか
        targetItemIndex = -1
    else:
        lst = lists.FileList()
        result = lst.Initialize(target)
        if result != errorCodes.OK:
            if result == errorCodes.ACCESS_DENIED and not ctypes.windll.shell32.IsUserAnAdmin():
                dlg = wx.MessageDialog(
                    None,
                    _("アクセスが拒否されました。管理者としてFalconを別ウィンドウで立ち上げて再試行しますか？"),
                    _("確認"),
                    wx.YES_NO | wx.ICON_QUESTION)
                if dlg.ShowModal() == wx.ID_YES:
                    misc.RunFile(sys.argv[0], True, target)
            return result  # アクセス不可
        if cursor != "":
            targetItemIndex = lst.Search(cursor)
        if isinstance(previous_tab, fileList.FileListTab):  # 再利用
            newtab = previous_tab
        else:
            newtab = fileList.FileListTab(environment)
            newtab.Initialize(parent, creator, hListCtrl)
        # end 再利用するかどうか
    newtab.Update(lst, targetItemIndex)
    # end ターゲットにフォーカス
    if globalVars.app.config['on_list_moved']['read_item_count'] == 'True':
        newtab.ReadListItemNumber(short=True)
    if newtab != previous_tab and previous_tab is not None:
        globalVars.app.hMainView.ReplaceCurrentTab(newtab)
    return newtab
# end Navigate
