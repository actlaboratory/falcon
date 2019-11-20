# -*- coding: utf-8 -*-
#Falcon file operation handler shortcut creation
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
import logging
import os
from win32com.shell import shell, shellcon
import win32com.client

from . import helper

VERB="shortcut"
log=logging.getLogger("falcon.%s" % VERB)

def Execute(op):
	"""実行処理。リトライが必要になった項目数を返す。"""
	try:
		target=op.instructions["target"]
	except KeyError:
		log.error("Required key is not specified.")
		return False
	#end 対象がない
	#target のパラメータはタプルで、 (out, source, args) の順番。
	op.output["all_OK"]=True
	op.output["retry"]["target"]=[]
	retry=0
	for elem in target:
		try:
			ws=win32com.client.Dispatch("wscript.shell")
			scut=ws.CreateShortcut(elem[0])
			scut.TargetPath=elem[1]
			scut.Arguments=elem[2]
			scut.Save()
		except Exception as err:
			log.error(err)
			appendRetry(op.output,elem)
		#end except
	#end for
	op.output["succeeded"]+=1
	if len(op.output["retry"]["target"])>0:
		op.output["retry"]["operation"]=VERB
		retry=len(op.output["retry"]["target"])
	#end リトライあるか
	return retry

def appendRetry(output,target):
	"""リトライするリストに追加する。"""
	output["retry"]["target"].append(target)
