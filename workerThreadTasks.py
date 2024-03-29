﻿# -*- coding: utf-8 -*-
# Falcon worker thread tasks
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.

"""
ワーカースレッドで実行されるタスクは、ここに並べます。
ワーカースレッドのタスクは、必ず taskState と param という辞書を引数にとり、それを使って処理します。
定期的に taskState.canceled プロパティをチェックして、 True になっていれば、処理を中断しなければなりません。その際には、 False を返します。処理を最後まで実行したら、 True を返す必要があります。
"""

import pathlib
import wx
import win32wnet
from win32com.shell import shell, shellcon
import globalVars
import misc
import time
import browsableObjects


def DirCalc(taskState, param):
    """
            計算結果は(インデックス番号,バイト単位のサイズint値)で返る。
            取得失敗時に-1となる場合があるので要注意
    """
    lst = param['lst']
    results = []
    for elem in lst:
        if taskState.canceled:
            return False
        s = misc.GetDirectorySize(elem[1])
        results.append((elem[0], s))
        # end 成功か失敗か
    # end for
    if taskState.canceled:
        return False
    wx.CallAfter(param['callback'], results, taskState)
    return True


def GetRecursiveFileList(taskState, param):
    """
            path から全てのフォルダを再帰的にたどって、ファイル名を out のリストに入れていく。なお、入る値は、 path からの相対パス。EOL=True にしておくと、ファイルリストを全部なめた段階で、eol という文字列をリストに追加してから終了する。検索終了の判定に使っている。
    """
    out_lst = param['out_lst']
    path = param['path']
    for elem in misc.IteratePaths(path):
        if taskState.canceled:
            return False
        out_lst.append(str(pathlib.Path(elem).relative_to(path)))
    # end ファイルリストをガンガン入れる
    if taskState.canceled:
        return False
    if param['eol']:
        out_lst.append('eol')
    return True


def PerformSearch(taskState, param):
    """
            検索のバックグラウンド処理。listObject の検索メソッドを実行して、見つかった者を tabObject のほうに通知しながら、リアルタイムな検索結果表示を実現している。
    """
    l = param['listObject']
    t = param['tabObject']
    while(True):
        if taskState.canceled:
            return False
        finished, hits = l._performSearchStep(taskState)
        if hits == -1:
            return False  # 検索処理からキャンセルで戻ってきた
        if len(hits) > 0:
            wx.CallAfter(t._onSearchHitCallback, hits, taskState)
        if finished:
            break  # 全て検索した
        time.sleep(0.1)
    # end 検索ループ
    return True

    for elem in misc.IteratePaths(param['path']):
        if taskState.canceled:
            return False


def DebugBeep(taskState, param):
    for i in range(10):
        if taskState.canceled:
            return False
        globalVars.app.PlaySound("tip.ogg")
        time.sleep(1)
    # end for
    return True


def GetNetworkResources(taskState=None, param=None):
    # 同期処理でも呼び出し可能。パラメータ無しで呼ぶ。
    sync_resources = []
    try:
        h = win32wnet.WNetOpenEnum(5, 1, 0, None)
        # 5=RESOURCE_CONTEXT
        # 1=RESOURCETYPE_DISK
        lst = win32wnet.WNetEnumResource(h, 64)  # 65以上の指定不可
        win32wnet.WNetCloseEnum(h)
    except win32net.error as er:
        if taskState:
            param["onFinish"](-1)  # コールバックに通知
            return True
        else:  # 同期処理
            raise err
            return None
        # end 同期処理
    # end 情報取得失敗
    if taskState and taskState.canceled:
        return False
    lst.pop(0)  # 先頭はドライブではない者が入るので省く
    for l in lst:
        ret, shfileinfo = shell.SHGetFileInfo(
            l.lpRemoteName, 0, shellcon.SHGFI_ICON)
        if taskState and taskState.canceled:
            return False
        addr = misc.ResolveLocalIpAddress(l.lpRemoteName[2:])
        s = browsableObjects.NetworkResource()
        s.Initialize(l.lpRemoteName[2:], l.lpRemoteName, addr, shfileinfo[0])
        if taskState and taskState.canceled:
            return False
        sync_resources.append(s)
        # end 同期処理
    # end 追加ループ
    if taskState and taskState.canceled:
        return False
    if taskState:
        if taskState:
            while(not param["isReady"]()):
                time.sleep(0.3)
            for s in sync_resources:
                wx.CallAfter(param["onAppend"], s)
        wx.CallAfter(param["onFinish"], len(lst))
        return True
    else:
        return sync_resources
