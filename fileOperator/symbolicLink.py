# -*- coding: utf-8 -*-
# Falcon file operation handler
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.
import logging
import os
import win32file
from . import helper

VERB = "symbolicLink"
log = logging.getLogger("falcon.%s" % VERB)


def Execute(op):
    """実行処理。リトライが必要になった項目数を返す。"""
    try:
        f = op.instructions["from"]
        t = op.instructions["to"]
    except KeyError as e:
        log.error("Required parameter is not specified %s." % e)
        return False
    # end 必要な情報がない
    op.output["all_OK"] = True
    op.output["retry"]["from"] = []
    op.output["retry"]["to"] = []
    i = 0
    retry = 0
    for elem in op.instructions["from"]:
        try:
            flag = 0
            if os.path.isdir(elem):
                flag = win32file.SYMBOLIC_LINK_FLAG_DIRECTORY

            # 相対パスで作成の場合
            if op.instructions["relative"]:
                elem = os.path.relpath(elem, start=os.path.dirname(t[i]))

            win32file.CreateSymbolicLink(
                t[i],
                elem,
                flag | win32file.SYMBOLIC_LINK_FLAG_ALLOW_UNPRIVILEGED_CREATE)  # これで、昇格しなくてもできるのか？
        except win32file.error as err:
            if helper.CommonFailure(op, elem, err, log):
                appendRetry(op.output, elem, t[i])
            continue
        # end except
        op.output["succeeded"] += 1
        i += 1
    # end 項目の数だけ
    if len(op.output["retry"]["from"]) > 0:
        op.output["retry"]["operation"] = VERB
        retry = len(op.output["retry"]["from"])
    # end リトライあるか
    return retry


def appendRetry(output, file, to):
    """リトライするリストに追加する。"""
    output["retry"]["from"].append(file)
    output["retry"]["to"].append(to)
