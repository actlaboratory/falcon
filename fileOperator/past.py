# -*- coding: utf-8 -*-
# Falcon file operation handler copy
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.
import logging
import os
import re
import time
import win32file
import winerror
from . import confirmElement, failedElement, helper
import reparse_link
from clipboard import COPY, MOVE

VERB = "past"
log = logging.getLogger("falcon.%s" % VERB)
"""テスト用のモックです。ディスクへの書き込みを待ち時間でシミュレートします。"""


class Element(object):
    """コピー/移動する項目の情報を持っておく。"""

    def __init__(self, path, basepath, destpath, is_link=False):
        """is_link=True の場合は、リンク先をたどらず、リンク自体を移動する。"""
        self.path = path
        self.is_link = is_link
        self.isfile = not reparse_link.is_directory_entry(path) if is_link else os.path.isfile(path)
        self.size = os.path.getsize(path) if self.isfile and not is_link else -1
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
    # 上書きを確認済みの項目が権限の昇格後に渡された場合も、確認済みとして扱う
    resume = resume or op.instructions.get("overwrite", False)
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
        op.output["percentage"] = 0
        op.output["copy_move_flag"] = copy_move_flag
    # end 初期化
    # 再開時に、前回リトライした項目をもう一度処理しないよう、毎回空にする
    op.output["retry"]["target"] = []
    log.debug("Retrieving file list...")
    lst = []
    for elemt in f:
        elem = elemt[0]
        dest = elemt[1]
        basepath = os.path.dirname(elem)
        if copy_move_flag == MOVE and reparse_link.is_link(elem):
            # リンク先の中身まで移動しないよう、リンク自体を移動する
            lst.append(Element(elem, basepath, dest, is_link=True))
        elif not os.path.exists(elem):  # コピーした後に削除された場合など
            _append_failed(op, Element(elem, basepath, dest), winerror.ERROR_FILE_NOT_FOUND, _("ファイルまたはフォルダが見つかりません。"))
        elif os.path.isfile(elem):
            lst.append(Element(elem, basepath, dest))
        else:
            e = Element(elem, basepath, dest)
            if os.path.isdir(e.destpath) and not resume:
                # フォルダがもうあれば、その時点で確認に入れる(中のフォルダを展開しない)
                # コピー先にディレクトリがあった時点で、「ディレクトリを上書きしますか？」の確認を出したいので。
                _processExistingFolder(op.output, elem, basepath, dest)
            else:  # まだないか、ユーザーに確認済みなので追加
                _expandFolder(op, lst, elem, e, basepath, dest, copy_move_flag)
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
    failed_folders = []  # 作成できなかったフォルダ。この中の項目は処理しない
    for elem in f:
        if any(elem.path == folder or elem.path.startswith(folder + os.sep) for folder in failed_folders):
            continue
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
        # リンクを経由して、同じ項目を自分自身に貼り付けようとしている場合
        if _is_same_item(elem):
            if not elem.isfile:
                failed_folders.append(elem.path)
            _append_failed(op, elem, winerror.ERROR_ALREADY_EXISTS, _("コピー元とコピー先が同じです。"))
            continue
        # フォルダ用のリンクで、すでにあるフォルダやリンクを上書きすることはできない
        if elem.is_link and not elem.isfile and os.path.lexists(elem.destpath):
            _append_failed(op, elem, winerror.ERROR_ALREADY_EXISTS, _("同じ名前のファイルまたはフォルダがすでに存在します。"))
            continue
        # 同じ名前のファイルとフォルダは、上書きも昇格もできない
        if os.path.exists(elem.destpath) and os.path.isfile(elem.destpath) != elem.isfile:
            if not elem.isfile:
                failed_folders.append(elem.path)
            _append_failed(op, elem, winerror.ERROR_ALREADY_EXISTS, _("同じ名前のファイルまたはフォルダがすでに存在します。"))
            continue
        try:
            if elem.is_link:
                reparse_link.move_link(elem.path, elem.destpath, overwrite)
            elif elem.isfile:
                copyOrMove(elem, copy_move_flag, overwrite)
            else:
                if resume and os.path.isdir(elem.destpath):
                    continue  # 再開している場合はエラーになる前に逃げる
                win32file.CreateDirectory(elem.destpath, None)
        except (win32file.error, OSError) as err:
            log.error("Cannot create %s (%s)" % (elem.destpath, str(err)))
            if not elem.isfile:
                failed_folders.append(elem.path)
            ProcessError(op, elem, err, resume)
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
        op.output["retry"]["copy_move_flag"] = copy_move_flag
        op.output["retry"]["overwrite"] = overwrite
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


def _is_same_item(elem):
    """コピー元とコピー先が、同じ項目かどうかを返す。"""
    try:
        return os.path.samefile(elem.path, elem.destpath)
    except OSError:
        return False  # どちらかがない


def ProcessError(op, elem, err, resume):
    """アクセス拒否であれば、リトライするリストに追加する。コピー先がすでに存在する場合は need_to_confirm に追加する。それ以外は失敗とする。"""
    number = err.winerror
    if helper.IsAccessDenied(number) and not op.elevated:  # アクセス拒否なので、リトライするリストに追加する
        op.output["retry"]["target"].append((elem.path, elem.destpath))
        return
    # end リトライ
    # コピー/移動先ファイルがすでに存在する
    if not resume and number in (winerror.ERROR_FILE_EXISTS, winerror.ERROR_ALREADY_EXISTS):
        # コピーでは80、移動では183になるが、「以降も同様に処理する」でまとめて応答できるよう番号をそろえる
        confirmation = confirmElement.ConfirmElement(elem, winerror.ERROR_FILE_EXISTS, _("このファイルはすでに存在します。"))
        op.output["need_to_confirm"].Append(confirmation)
        op._doCallback("confirm", confirmation)
        return
    # end 要確認
    _append_failed(op, elem, number, err.strerror)
# end ProcessError


def _append_failed(op, elem, number, msg):
    """項目を、失敗したリストに追加する。"""
    op.output["all_OK"] = False
    op.output["failed"].append(failedElement.FailedElement(elem.path, (number, msg)))


def _processExistingFolder(output, elem, basepath, destpath):
    """指定したフォルダを、すでに存在するフォルダとして、 need_to_confirm に入れる。"""
    output["need_to_confirm"].Append(confirmElement.ConfirmElement(
        Element(elem, basepath, destpath), 80, _("このフォルダはすでに存在します。")))


def _expandFolder(op, lst, path, e, basepath, destpath, copy_move_flag, parents=()):
    """フォルダを展開して、指定されたリストに入れる。"""
    # コピーではリンク先の中身をたどるので、同じフォルダを繰り返したどらないようにする
    real_path = os.path.normcase(os.path.realpath(path))
    if real_path in parents:
        _append_failed(op, e, winerror.ERROR_CANT_RESOLVE_FILENAME, _("リンク先が自身を含むフォルダのため、コピーできません。"))
        return
    parents += (real_path,)
    lst.append(e)  # イテレーションの最初に親フォルダ追加
    # 再帰的にディレクトリを掘っていく。切り取りモードの時にフォルダ削除マークを入れたいので、iteratePaths計で一気に取得することはできない。
    try:
        names = os.listdir(path)
    except OSError as err:
        log.error("Cannot list %s (%s)" % (path, str(err)))
        _append_failed(op, e, err.winerror, err.strerror)
        return
    for elem in names:
        p = os.path.join(path, elem)
        innerDestpath = os.path.join(destpath, os.path.basename(p))
        if copy_move_flag == MOVE and reparse_link.is_link(p):
            lst.append(Element(p, basepath, innerDestpath, is_link=True))
            continue
        innerElem = Element(p, basepath, innerDestpath)
        if not os.path.exists(p):  # リンク先がないリンクなど
            _append_failed(op, innerElem, winerror.ERROR_FILE_NOT_FOUND, _("ファイルまたはフォルダが見つかりません。"))
        elif os.path.isdir(p):
            # フォルダなので、再帰的に中身を転回
            _expandFolder(op, lst, p, innerElem, basepath,
                          innerDestpath, copy_move_flag, parents)
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
