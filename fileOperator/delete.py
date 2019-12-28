# -*- coding: utf-8 -*-
#Falcon file operation handler delete
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
import logging
import os
import win32file

from . import helper

VERB="delete"
log=logging.getLogger("falcon.%s" % VERB)

def Execute(op):
	"""実行処理。リトライが必要になった項目数を返す。"""
	retry=0
	try:
		f=op.instructions["target"]
	except KeyError:
		log.error("Required key is not specified.")
		return False
	#end 処理刷るものなし
	op.output["all_OK"]=True
	op.output["retry"]["target"]=[]
	lst=[]
	for elem in f:
		if os.path.isfile(elem):
			lst.append(elem)
		else:
			for elem2 in misc.IteratePaths(elem):
				lst.append(elem2)
			#end フォルダからファイルリスト
		#end フォルダだった
	#end ファイルリスト作るループ
	#ファイルリスト作ったので、もともとの target に上書き
	f=lst
	for elem in f:
		try:
			if os.path.isfile(elem):
				win32file.DeleteFile(elem)
			else:
				win32file.RemoveDirectory(elem)
		except win32file.error as err:
			appendRetry(op.output,elem)
			continue
		#end except
		op.output["succeeded"]+=1
	#end 削除処理
	if len(op.output["retry"]["target"])>0:
		op.output["retry"]["operation"]=VERB
		retry=len(op.output["retry"]["target"])
	#end リトライあるか
	return retry

def appendRetry(output,target):
	"""リトライするリストに追加する。"""
	output["retry"]["target"].append(target)
