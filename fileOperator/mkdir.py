# -*- coding: utf-8 -*-
# Falcon file operation handler make new directory
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.
import logging
import os
import win32file
from . import helper

VERB = "mkdir"
log = logging.getLogger("falcon.%s" % VERB)


def Execute(op):
    """実行処理。リトライが必要になった項目数を返す。"""
    try:
        target = op.instructions["target"]
    except KeyError:
        log.error("target is not specified.")
        return False
    # end 新規フォルダ名がない
    op.output["all_OK"] = True
    op.output["retry"]["target"] = []
    i = 0
    retry = 0
    for elem in target:
        try:
            win32file.CreateDirectory(elem, None)
        except win32file.error as err:
            if helper.CommonFailure(op, elem, err, log):
                appendRetry(op.output, elem)
            continue
        # end except
        op.output["succeeded"] += 1
        i += 1
    # end 項目の数だけ
    if len(op.output["retry"]["target"]) > 0:
        op.output["retry"]["operation"] = VERB
        retry = len(op.output["retry"]["target"])
    # end リトライあるか
    return retry


def appendRetry(output, target):
    """リトライするリストに追加する。"""
    output["retry"]["target"].append(target)
