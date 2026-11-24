# -*- coding: utf-8 -*-
# Falcon file operation handler rename
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.
import logging
import os
import win32file
from . import helper

VERB = "rename"
log = logging.getLogger("falcon.%s" % VERB)


def Execute(op):
    """実行処理。リトライが必要になった項目数を返す。"""
    try:
        to = op.instructions["to"]
    except KeyError:
        log.error("To is not specified.")
        return False
    # end 変更先がない
    op.output["all_OK"] = True
    op.output["retry"]["to"] = []
    retry = 0
    # 失敗した項目で次に進むときも、変更先がずれないように zip で対応づける
    for elem, dest in zip(op.instructions["files"], to):
        isdrive = "\\" not in elem
        log.debug("from %s, to %s, isdrive %s" % (elem, dest, isdrive))
        if isdrive:
            d = elem[0] + ":\\"
            try:
                win32file.SetVolumeLabel(d, dest)
            except win32file.error as err:
                if helper.CommonFailure(op, elem, err, log):
                    appendRetry(op.output, elem, dest)
                continue
            # end except
        else:  # ファイルだからリネーム
            try:
                win32file.MoveFile(elem, dest)
            except win32file.error as err:
                if helper.CommonFailure(op, elem, err, log):
                    appendRetry(op.output, elem, dest)
                continue
            # end except
        # end ファイルかドライブか
        op.output["succeeded"] += 1
    # end 項目の数だけ
    if len(op.output["retry"]["files"]) > 0:
        op.output["retry"]["operation"] = VERB
        retry = len(op.output["retry"]["files"])
    # end リトライあるか
    return retry


def appendRetry(output, file, to):
    """リトライするリストに追加する。"""
    output["retry"]["files"].append(file)
    output["retry"]["to"].append(to)
