# -*- coding: utf-8 -*-
#Falcon file operation handler trash
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
import logging
import os
from win32com.shell import shell, shellcon

from . import helper

VERB="trash"
log=logging.getLogger("falcon.%s" % VERB)

def Execute(op):
	"""実行処理。リトライが必要になった項目数を返す。"""
	retry=0
	try:
		f=op.instructions["target"]
	except KeyError:
		log.error("Required key is not specified.")
		return False
	#end ゴミ箱に入れるファイルリストがない
	op.output["all_OK"]=True
	op.output["retry"]["target"]=[]
	for elem in f:
		sh=(
			0,
			shellcon.FO_DELETE,
			elem,
			None,
			shellcon.FOF_ALLOWUNDO|shellcon.FOF_NOCONFIRMATION|shellcon.FOF_NO_UI,
			None,
			""
		)
		ret=shell.SHFileOperation(sh)
		if ret[0]!=0:
			if helper.CommonFailure(op,elem,ret[0],log): appendRetry(op.output,elem)
		#end except
		op.output["succeeded"]+=1
	#end ゴミ箱ループ
	if len(op.output["retry"]["target"])>0:
		op.output["retry"]["operation"]=VERB
		retry=len(op.output["retry"]["target"])
	#end リトライあるか
	return retry

def appendRetry(output,target):
	"""リトライするリストに追加する。"""
	output["retry"]["target"].append(target)
