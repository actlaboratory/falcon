# -*- coding: utf-8 -*-
#Falcon generic list management
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import sys
import os
import gettext
import wx
import constants
import configparser
from simpleDialog import *

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
		self.rootDirectory=dir
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

	def GetItems(self):
		"""リストの中身を取得する。フォルダが上にくる。"""
		return self.folders+self.files
