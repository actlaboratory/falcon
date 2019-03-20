# -*- coding: utf-8 -*-
#Falcon generic list management
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import os
import logging
import win32api
import misc
class FalconListBase(object):
	"""全てのリストに共通する基本クラス。"""
	def __init__(self):
		pass

	def __del__(self):
		pass

class FileList(FalconListBase):
	"""ファイルとフォルダの一覧を扱うリスト。"""
	def Initialize(self,dir):
		"""ディレクトリからファイル情報を取得し、リストを初期化する。入力は絶対パスでなければならない。"""
		self.log=logging.getLogger("falcon.fileList")
		self.rootDirectory=dir
		self.log.debug("Getting file list for %s..." % self.rootDirectory)
		t=misc.Timer()
		lst=win32api.FindFiles(dir+"\\*")
		self.files=[]
		self.folders=[]
		del lst[0:2]
		for elem in lst:
			fullpath=dir+"\\"+elem[8]
			add=[]
			add.append(elem[8])#ファイル名
			add.append((elem[4]<<32)+elem[5])#ファイルサイズ
			add.append("undefined")#更新
			add.append("undefined")#属性
			add.append("undefined")#種類
			if os.path.isfile(fullpath):
				self.files.append(add)
			else:
				self.folders.append(add)
			#end どっちについかするか？
		#end 追加ループ
		self.log.debug("File list created in %d milliseconds." % t.elapsed)

	def GetItems(self):
		"""リストの中身を取得する。フォルダが上にくる。"""
		return self.folders+self.files
