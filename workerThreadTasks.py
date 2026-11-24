# -*- coding: utf-8 -*-
# Falcon worker thread tasks
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.

"""
ワーカースレッドで実行されるタスクは、ここに並べます。
ワーカースレッドのタスクは、必ず taskState と param という辞書を引数にとり、それを使って処理します。
定期的に taskState.canceled プロパティをチェックして、 True になっていれば、処理を中断しなければなりません。その際には、 False を返します。処理を最後まで実行したら、 True を返す必要があります。
"""

import logging
import pathlib
import wx
import pywintypes
import globalVars
import misc
import network_resource
import time
import browsableObjects

log = logging.getLogger("falcon.workerThreadTasks")


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
        globalVars.app.play_sound("tip.ogg")
        time.sleep(1)
    # end for
    return True


def GetNetworkResources(taskState, param):
    """
        ネットワーク上のコンピューターを探し、見つかるたびに onAppend で通知する。
        終わったら onFinish に見つかった数(取得できなかった場合は-1)を渡す。
    """
    while not param["isReady"]():
        if taskState.canceled:  # タブが閉じられた
            return False
        time.sleep(0.3)
    resources = []

    def on_found(name, path, hIcon):
        resource = browsableObjects.NetworkResource()
        resource.Initialize(name, path, "", hIcon)
        resources.append(resource)
        wx.CallAfter(param["onAppend"], resource, taskState)

    try:
        completed = network_resource.enumerate_computers(on_found, lambda: taskState.canceled)
    except pywintypes.com_error as err:
        log.warning("Cannot enumerate network computers: %s" % err)
        if taskState.canceled:
            return False
        wx.CallAfter(param["onFinish"], -1)
        return True
    if not completed:
        return False
    wx.CallAfter(param["onFinish"], len(resources))
    # 名前の解決には時間がかかることがあるため、一覧に出した後で行う
    for resource in resources:
        if taskState.canceled:
            return False
        resource.address = misc.ResolveLocalIpAddress(resource.fullpath[2:])
    return True
