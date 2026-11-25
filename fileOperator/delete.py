# -*- coding: utf-8 -*-
# Falcon file operation handler delete
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.
import logging
import os
import win32file

import misc
import reparse_link

from . import helper

VERB = "delete"
log = logging.getLogger("falcon.%s" % VERB)


def Execute(op):
    """実行処理。リトライが必要になった項目数を返す。"""
    retry = 0
    try:
        f = op.instructions["target"]
    except KeyError:
        log.error("Required key is not specified.")
        return False
    # end 処理刷るものなし
    op.output["all_OK"] = True
    op.output["retry"]["target"] = []
    op.output["percentage"] = 0
    op.is_counting = True
    lst = []
    for elem in f:
        if op.is_canceled():
            break
        # リンクの場合は、リンク先の中身を消さないよう、リンク自体だけを削除する
        if not reparse_link.is_directory_entry(elem) or reparse_link.is_link(elem):
            lst.append(elem)
        else:
            for elem2 in misc.IteratePaths(elem, follow_links=False):
                if op.is_canceled():
                    break
                lst.append(elem2)
            # end フォルダからファイルリスト
            lst.append(elem)  # イテレーションの最後に親フォルダ追加
        # end フォルダだった
    # end ファイルリスト作るループ
    # ファイルリスト作ったので、もともとの target に上書き
    f = lst
    op.is_counting = False
    for index, elem in enumerate(f):
        if op.is_canceled():
            log.info("canceled")
            break
        percentage = index * 100 // len(f)
        if percentage != op.GetPercentage():
            op.SetPercentage(percentage)
        try:
            if reparse_link.is_directory_entry(elem):
                win32file.RemoveDirectory(elem)
            else:
                win32file.DeleteFile(elem)
        except win32file.error as err:
            if helper.CommonFailure(op, elem, err, log):
                appendRetry(op.output, elem)
            continue
        # end except
        op.output["succeeded"] += 1
    # end 削除処理
    if op.is_canceled():
        op.output["retry"]["target"] = []
    if len(op.output["retry"]["target"]) > 0:
        op.output["retry"]["operation"] = VERB
        retry = len(op.output["retry"]["target"])
    # end リトライあるか
    return retry


def appendRetry(output, target):
    """リトライするリストに追加する。"""
    output["retry"]["target"].append(target)
