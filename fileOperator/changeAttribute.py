# -*- coding: utf-8 -*-
# Falcon file operation handler rename
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.
import logging
import os
import win32file
from . import helper

VERB = "changeAttribute"
log = logging.getLogger("falcon.%s" % VERB)


def Execute(op):
    """実行処理。リトライが必要になった項目数を返す。"""
    try:
        to_attrib = op.instructions["to_attrib"]
    except KeyError:
        log.error("To_attrib or to_date is not specified.")
        return False
    # end 変更先がない
    op.output["all_OK"] = True
    op.output["retry"]["from"] = []
    op.output["retry"]["to_attrib"] = []
    i = 0
    retry = 0
    for elem in op.instructions["from"]:
        try:
            win32file.SetFileAttributes(elem, to_attrib[i])
        except win32file.error as err:
            if helper.CommonFailure(op, elem, err, log):
                appendRetry(op.output, elem, to[i])
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


"""
日時変更に使っていたコード
		try:
			hFile=win32file.CreateFile(elem,win32file.GENERIC_READ|win32file.GENERIC_WRITE,0,None,win32file.OPEN_EXISTING,0,None)
			c=pywintypes.Time(to_date[0]) if to_date[0] is not None else None
			m=pywintypes.Time(to_date[1]) if to_date[1] is not None else None
			win32file.SetFileTime(hFile,c,None,m)
			win32api.CloseHandle(hFile)
		except win32file.error as err:
			if helper.CommonFailure(op,elem,err,log): appendRetry(op.output,elem,to[i])
			continue
		#end except
"""
