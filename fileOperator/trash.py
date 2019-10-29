# -*- coding: utf-8 -*-
#Falcon file operation handler trash
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
import logging
import os
from win32com import shell, shellcon

from . import helper

VERB="trash"
log=logging.getLogger("falcon.%s" % VERB)

def Execute(op):
	"""実行処理。リトライが必要になった項目数を返す。"""
	try:
		from=op.instructions["from"]
	except KeyError:
		log.error("from is not specified.")
		return False
	#end ゴミ箱に入れるファイルリストがない
	op.output["all_OK"]=True
	op.output["retry"]["from"]=[]
	sh=(
		0,
		shellcon.FO_DELETE,
		"\0".join(from),
		None,
		shellcon.FOF_ALLOWUNDO,
		None,
		_("ゴミ箱に移動しています…")
	)
	try:
		ret=shell.SHFileOperation(sh)
	except win32con.error as err:
		#SHFileOperation で一気に処理されてしまうので、commonFailure が通しにくい
		appendRetry(op.output,from)
	#end except
	op.output["succeeded"]+=1
	if len(op.output["retry"]["target"])>0:
		op.output["retry"]["operation"]=VERB
		retry=len(op.output["retry"]["from"])
	#end リトライあるか
	return retry

def appendRetry(output,target):
	"""リトライするリストに追加する。"""
	output["retry"]["from"].append(target)
