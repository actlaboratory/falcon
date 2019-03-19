# -*- coding: utf-8 -*-
#Falcon generic list management
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import os
import logging
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
		lst=os.listdir(dir )
		self.files=[]
		self.folders=[]
		for elem in lst:
			fullpath=dir+"\\"+elem
			add=[]
			add.append(elem)
			add.append("undefined")
			add.append("undefined")
			add.append("undefined")
			add.append("undefined")
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
