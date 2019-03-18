# -*- coding: utf-8 -*-
#Falcon tab management
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
タブは、必ずリストビューです。カラムの数と名前と、それに対応するリストの要素がタブを構成します。たとえば、ファイル一覧では「ファイル名」や「サイズ」などがカラムになり、その情報がリストに格納されています。ファイル操作の状況を示すタブの場合は、「進行率」や「状態」などがカラムの名前として想定されています。
"""

import sys
import os
import gettext
import constants
import listObjects
from simpleDialog import *

class FalconTabBase(object):
	"""全てのタブに共通する基本クラス。"""
	def __init__(self):
		self.colums=[]#タブに表示されるカラムの一覧。外からは読み取りのみ。
		self.listObject=None#リストの中身を保持している listObjects のうちのどれかのオブジェクト・インスタンス
	def __del__(self):
		pass

	def GetColumns(self):
		return self.columns

	def GetItems(self):
		"""タブのリストの中身を取得する。"""
		return self.listObject.GetItems() if self.listObject is not None else []

class FileListTab(FalconTabBase):
	"""ファイルリストが表示されているタブ。"""
	def Initialize(self,dir):
		"""タブを初期化する。ディレクトリ名の指定で、ファイルリストを作成する。"""
		#カラム設定
		self.columns=[_("ファイル名"),_("サイズ"),_("更新"),_("属性"),_("種類")]
		self.listObject=listObjects.FileList()
		self.listObject.Initialize(dir)

