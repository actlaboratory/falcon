# -*- coding: utf-8 -*-
# Falcon file operation handler copy
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.
import logging
import os
import re
import time
import win32file
from . import confirmElement, failedElement, helper
import misc
from clipboard import COPY, MOVE

VERB = "past"
log = logging.getLogger("falcon.%s" % VERB)
"""テスト用のモックです。ディスクへの書き込みを待ち時間でシミュレートします。"""


class Element(object):
    """コピー/移動する項目の情報を持っておく。"""

    def __init__(self, path, basepath, destpath):
        self.path = path
        self.isfile = os.path.isfile(path)
        self.size = os.path.getsize(path) if self.isfile else -1
        self.destpath = destpath
    # end __init__

    def __str__(self):
        return "past element (path=%s, destpath=%s, size=%d)" % (self.path, self.destpath, self.size)
    # end __str__
# end Element


def Execute(op, resume=False):
    """実行処理。リトライが必要になった項目数を返す。"""
    if resume:
        log.debug("Starting as resume mode...")
    retry = 0
    try:
        f = op.instructions["target"]
    except KeyError:
        log.error("Required key is not specified.")
        return False
    # end 処理刷るものなし
    copy_move_flag = op.instructions["copy_move_flag"]
    if not resume:  # resume modeではない=初期化
        op.output["all_OK"] = True
        op.output["retry"]["target"] = []
        op.output["percentage"] = 0
        op.output["copy_move_flag"] = copy_move_flag
    # end 初期化
    log.debug("Retrieving file list...")
    lst = []
    for elemt in f:
        elem = elemt[0]
        dest = elemt[1]
        basepath = os.path.dirname(elem)
        if os.path.isfile(elem):
            lst.append(Element(elem, basepath, dest))
        else:
            e = Element(elem, basepath, dest)
            if os.path.isdir(e.destpath) and not resume:
                # フォルダがもうあれば、その時点で確認に入れる(中のフォルダを展開しない)
                # コピー先にディレクトリがあった時点で、「ディレクトリを上書きしますか？」の確認を出したいので。
                _processExistingFolder(op.output, elem, basepath, destpath)
            else:  # まだないか、ユーザーに確認済みなので追加
                _expandFolder(lst, elem, e, basepath, dest, copy_move_flag)
            # end フォルダを展開するかしないか
        # end フォルダだった
    # end ファイルリスト作るループ
    # ファイルリスト作ったので、もともとの target に上書き
    f = lst
    log.debug("%d items found." % len(f))
    # コピーサイズの合計を計算
    total = 0
    for elem in f:
        if elem.size != -1:
            total += elem.size
    # end サイズを足す
    op.output['total_bytes'] = total
    op.output['current_bytes'] = 0
    log.debug("Size: %d bbytes" % total)
    log.debug("Start copying...")
    overwrite = resume
    pasted_size = 0
    for elem in f:
        if elem.destpath is None:  # フォルダ削除用
            # 移動するとき、 destpath が空のエントリーは、フォルダを消すという命令代わりに使っている。
            log.debug("deleting folder %s" % elem.path)
            try:
                win32file.RemoveDirectory(elem.path, None)
            except win32file.error as err:
                log.debug(
                    "Error encountered when trying to delete moved folder: %s" %
                    str(err))
            # end except
            continue  # エラーにならないように逃げる
        # end フォルダ消す
        try:
            if elem.isfile:
                copyOrMove(elem, copy_move_flag, overwrite)
            else:
                if resume and os.path.isdir(elem.destpath):
                    continue  # 再開している場合はエラーになる前に逃げる
                win32file.CreateDirectory(elem.destpath, None)
        except win32file.error as err:
            log.error("Cannot create %s (%s)" % (elem.destpath, str(err)))
            ProcessError(op, elem, str(err), resume)
            continue
        # end except
        op.output["succeeded"] += 1
        if elem.size != -1:
            pasted_size += elem.size
        if total == 0:
            percentage = 100
        else:
            percentage = int(pasted_size / total * 100)
        op.SetPercentage(percentage)
    # end 削除処理
    if len(op.output["retry"]["target"]) > 0:
        op.output["retry"]["operation"] = VERB
        retry = len(op.output["retry"]["target"])
    # end リトライあるか
    # 終わった者はもう使わないので、ファイルリストは消してしまう
    op.instructions["target"] = []
    return retry

def copyOrMove(elem, copy_move_flag, overwrite):
    if copy_move_flag == COPY:
        f = 0 if overwrite else win32file.COPY_FILE_FAIL_IF_EXISTS
        win32file.CopyFileEx(
            elem.path, elem.destpath, None, None, False, f
        )
    else:
        f = win32file.MOVEFILE_COPY_ALLOWED | win32file.MOVEFILE_REPLACE_EXISTING if overwrite else win32file.MOVEFILE_COPY_ALLOWED
        win32file.MoveFileEx(elem.path, elem.destpath, f)

def ProcessError(op, elem, msg, resume):
    """アクセス拒否であれば、リトライするリストに追加する。昇格しても失敗するエラーであれば、 need_to_confirm に追加する。"""
    number = helper.GetErrorNumber(msg)
    if helper.IsAccessDenied(number):  # アクセス拒否なので、リトライするリストに追加する
        op.output["retry"]["target"].append(elem)
        return
    # end リトライ
    # コピー/移動先ファイルがすでに存在する
    if number == 80 or number == 183:
        op.output["need_to_confirm"].Append(
            confirmElement.ConfirmElement(
                elem, number, msg))
        op._doCallback("confirm", elem)
        return
    # end 要確認
    output["all_OK"] = False
    output["failed"].append(
        failedElement.FailedElement(
            elem.destpath, (number, msg)))
# end ProcessError


def _processExistingFolder(output, elem, basepath, destpath):
    """指定したフォルダを、すでに存在するフォルダとして、 need_to_confirm に入れる。"""
    output["need_to_confirm"].Append(confirmElement.ConfirmElement(
        Element(elem, basepath, destpath), 80, _("このフォルダはすでに存在します。")))


def _expandFolder(lst, path, e, basepath, destpath, copy_move_flag):
    """フォルダを展開して、指定されたリストに入れる。"""
    lst.append(e)  # イテレーションの最初に親フォルダ追加
    # 再帰的にディレクトリを掘っていく。切り取りモードの時にフォルダ削除マークを入れたいので、iteratePaths計で一気に取得することはできない。
    for elem in os.listdir(path):
        p = os.path.join(path, elem)
        innerDestpath = os.path.join(destpath,os.path.basename(p))
        innerElem = Element(p, basepath, innerDestpath)
        if os.path.isdir(p):
            # フォルダなので、再帰的に中身を転回
            _expandFolder(lst, p, innerElem, basepath,
                          innerDestpath, copy_move_flag)
            _handleFolderDeleteRecord(lst, innerElem, basepath, copy_move_flag)
        else:
            # ファイルなのでそのまま追加
            lst.append(innerElem)
        # end フォルダかファイルか
    # end 追加処理
    # 移動モードの時、フォルダの最後に、そのフォルダを削除するためのエレメントを挿入する
    _handleFolderDeleteRecord(lst, e, basepath, copy_move_flag)
    # end
# end _expandFolder


def _handleFolderDeleteRecord(lst, e, basepath, copy_move_flag):
    if copy_move_flag == MOVE:
        lst.append(Element(e.path, basepath, None))
