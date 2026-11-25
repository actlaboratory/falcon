# -*- coding: utf-8 -*-
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
import background_wait
import errorCodes
import lists
import globalVars
import constants
import misc
import network_resource
import pywintypes
import views.ViewCreator
from . import fileList, driveList, streamList, searchResult, grepResult, NetworkResourceList
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
        # かならずviews.Main.Navigateを経由して呼び出されているはず
        return newtab
    # end targetが辞書の時の特殊処理

    target = os.path.expandvars(target)
    if target != "" and not network_resource.is_server_path(target):
        # ネットワーク上の場所で認証が必要な場合は、資格情報の入力画面が出る
        try:
            status = network_resource.check_path_with_auth(target, globalVars.app.main_window.GetHandle())
        except background_wait.Canceled:
            return errorCodes.CANCELED
        except pywintypes.error as err:
            log.error("navigate failed: cannot connect to %s: %s" % (target, err))
            if network_resource.is_connection_error(err.winerror):
                dialog(_("エラー"), network_resource.get_connection_error_message(target, err.strerror))
                return errorCodes.NETWORK_UNAVAILABLE
            if not network_resource.is_cancelled_error(err):
                dialog(_("エラー"), _("移動に失敗しました(%(error)s)") % {"error": err.strerror})
            return errorCodes.ACCESS_DENIED
        if status.is_connection_error():
            log.error("navigate failed: cannot connect to %s: %s" % (target, status.message))
            dialog(_("エラー"), network_resource.get_connection_error_message(target, status.message))
            return errorCodes.NETWORK_UNAVAILABLE
        if not status.exists:
            log.error("navigate failed: %s not exist." % target)
            dialog(_("エラー"), _("移動に失敗しました。移動先が存在しません。"))
            return errorCodes.FILE_NOT_FOUND
    if target == "":  # ドライブリスト
        lst = lists.DriveList()
        lst.Initialize()
        if isinstance(previous_tab, driveList.DriveListTab):  # 再利用
            newtab = previous_tab
            newtab.OnUpdate()  # 新しい一覧にはネットワーク上のコンピューターがないので、探し直す
        else:
            newtab = driveList.DriveListTab(environment)
            newtab.Initialize(parent, creator, hListCtrl)
        # end 再利用するかどうか
        targetItemIndex = lst.Search(cursor, 1)
        if targetItemIndex == -1 and cursor != "":  # ネットワークドライブ対策
            targetItemIndex = lst.Search(cursor, 0)
    # end ドライブリストへ行く
    elif network_resource.is_server_path(target):
        target = target.rstrip("\\")
        lst = lists.NetworkResourceList()
        result = lst.Initialize(target)
        if result != errorCodes.OK:
            return result  # アクセス不可
        if cursor != "":
            targetItemIndex = lst.Search(cursor)
        newtab = NetworkResourceList.NetworkResourceListTab(environment)
        newtab.Initialize(parent, creator, hListCtrl)
    elif status.is_file:  # 副ストリームへ移動
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
            if result == errorCodes.ACCESS_DENIED and network_resource.is_unc_path(target):
                # ネットワーク上のフォルダは、管理者として立ち上げ直しても開けるようにならない
                dialog(_("エラー"), _("アクセスが拒否されました。"))
            elif result == errorCodes.ACCESS_DENIED and not ctypes.windll.shell32.IsUserAnAdmin():
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
    if target == "" and targetItemIndex == -1 and network_resource.is_server_path(cursor):
        newtab.set_pending_focus(cursor)
    # end ターゲットにフォーカス
    if globalVars.app.settings.get_bool("on_list_moved", "read_item_count", True):
        newtab.ReadListItemNumber(short=True)
    if newtab != previous_tab and previous_tab is not None:
        globalVars.app.main_window.replace_current_tab(newtab)
    return newtab
# end Navigate


def go_to_parent(tab, path):
    """
    path を含むフォルダへ移動する。なくなっている場合は、存在するフォルダまでさかのぼる。
    たどり着けない場合は、共有フォルダならコンピューター、それ以外ならドライブ一覧へ移動する。
    ネットワークに接続できない場合は、エラーを知らせてドライブ一覧へ移動する。
    """
    is_unc = network_resource.is_unc_path(path)
    cursor_for_drive_list = network_resource.get_server_path(path) if is_unc else path[0]
    current = path
    while True:
        parent, name = os.path.split(current)
        if parent == current or name == "":
            break
        try:
            status = network_resource.check_path(parent)
        except background_wait.Canceled:
            return errorCodes.CANCELED
        if status.is_connection_error():
            log.error("cannot connect to %s: %s" % (parent, status.message))
            dialog(_("エラー"), network_resource.get_connection_error_message(parent, status.message))
            return tab.Move("", cursor_for_drive_list)
        if status.exists and not status.is_file:
            return tab.Move(parent, name)
        current = parent
    if is_unc:
        server = network_resource.get_server_path(path)
        result = tab.Move(server, os.path.splitdrive(path)[0][len(server) + 1:])
        if not isinstance(result, int) or result in (errorCodes.OK, errorCodes.CANCELED):
            return result
    return tab.Move("", cursor_for_drive_list)
