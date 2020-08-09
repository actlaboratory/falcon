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
		dest=os.path.abspath(elem[0])
		source=elem[1]
		if elem[4]:			#相対パスで作成
			source=os.path.relpath(source,start=os.path.dirname(dest))
			if elem[3]!="":
				parameter="/C start /D \""+elem[3]+"\" \""+source+"\" "+elem[2]
			else:
				parameter="/C \""+source+"\" "+elem[2]
			source="%windir%\\system32\\cmd.exe"
			workDir=""		#スクリプト上で指定するのでショートカットには入れない
			windowStyle=7	#最小化
		else:				#絶対パスで作成
			workDir=elem[3]
			parameter=elem[2]
			windowStyle=1	#通常

		if os.path.isfile(dest):
			helper.AppendFailed(op,elem,183)#file_already_exists
			continue
		#end 上書き防止
		try:
			ws=win32com.client.Dispatch("wscript.shell")
			scut=ws.CreateShortcut(dest)
			scut.TargetPath=source
			scut.Arguments=parameter
			scut.WorkingDirectory=workDir
			scut.WindowStyle=windowStyle
			scut.Save()
		except Exception as err:
			log.error(err)
			appendRetry(op.output,elem)
		#end except
		op.output["succeeded"]+=1
	#end for
	if len(op.output["retry"]["target"])>0:
		op.output["retry"]["operation"]=VERB
		retry=len(op.output["retry"]["target"])
	#end リトライあるか
	return retry

def appendRetry(output,target):
	"""リトライするリストに追加する。"""
	output["retry"]["target"].append(target)
