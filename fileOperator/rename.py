# -*- coding: utf-8 -*-
#Falcon file operation handler rename
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
import logging
import os
import win32file
from . import helper

log=logging.getLogger("falcon.rename")

def Execute(instructions,output):
		"""実行処理。"""
		try:
			to=instructions["to"]
		except KeyError:
			log.error("To is not specified.")
			return
		#end 変更先がない
		output["all_OK"]=True
		i=0
		for elem in instructions["files"]:
			isdrive=not "\\" in elem
			log.debug("from %s, to %s, isdrive %s" % (elem, to[i], isdrive))
			if isdrive:
				d=elem[0]+":\\"
				try:
					win32file.SetVolumeLabel(d,to[i])
				except win32file.error as err:
					helper.CommonFailure(output,{"file": elem, "to": to[i]},err,log)
					continue
				#end except
			else:#ファイルだからリネーム
				try:
					win32file.MoveFile(elem,to[i])
				except win32file.error as err:
					helper.CommonFailure(output,{"file": elem, "to": to[i]},err,log)
					continue
				#end except
			#end ファイルかドライブか
			output["succeeded"]+=1
			i+=1
		#end 項目の数だけ
