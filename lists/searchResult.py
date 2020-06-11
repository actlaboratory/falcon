# -*- coding: utf-8 -*-
#Falcon search results list object
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import os
import re
import wx
import browsableObjects
import globalVars
import errorCodes

from .searchResultBase import *
from .constants import *

class SearchResultList(SearchResultBase):
	"""ファイルとフォルダの一覧を扱うリスト。"""
	def __init__(self):
		super().__init__()
		self.supportedSorts=[SORT_TYPE_BASENAME,SORT_TYPE_FILESIZE,SORT_TYPE_SEARCHPATH,SORT_TYPE_MODDATE,SORT_TYPE_ATTRIBUTES,SORT_TYPE_TYPESTRING]
		self.columns={
			_("ファイル名"):wx.LIST_FORMAT_LEFT,
			_("サイズ"):wx.LIST_FORMAT_RIGHT,
			_("検索パス"):wx.LIST_FORMAT_LEFT,
			_("更新"):wx.LIST_FORMAT_LEFT,
			_("属性"):wx.LIST_FORMAT_LEFT,
			_("種類"):wx.LIST_FORMAT_LEFT
		}
		self.folders=[]
		self.files=[]
		self.lists=[self.folders,self.files]

	def Initialize(self,rootDirectory,searches=[],keyword="",isRegularExpression=False,silent=False):
		"""与えられたファイル名のリストから、条件に一致する項目を抽出する。"""
		if isinstance(rootDirectory,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			for elem in rootDirectory:
				if type(elem) is browsableObjects.SearchedFolder:
					self.folders.append(elem)
				else:
					self.files.append(elem)
				#end ファイルかフォルダか
			#end for
			return errorCodes.OK
		self.rootDirectory=rootDirectory
		self.searches=searches
		self._initKeyword(keyword,isRegularExpression,silent)
		self._initSearch()

	def HitTest(self,path,ret_list):
		"""_performSearchStepから呼ばれ、与えられたpathのファイルが検索にヒットするならリスト追加する"""
		if re.search(self.keyword,path):
			fullpath=os.path.join(self.rootDirectory,path)
			if os.path.isfile(fullpath):
				f=self._MakeObject(browsableObjects.SearchedFile,fullpath)
				self.files.append(f)
			else:
				f=self._MakeObject(browsableObjects.SearchedFolder,fullpath,True)
				self.folders.append(f)
			#end ファイルかフォルダか
			ret_list.append(f)
			return 1
		return 0

	def GetFolderFileNumber(self):
		return len(self.folders), len(self.files)

	def GetTopFileIndex(self):
		"""先頭ファイルのインデックス番号を返す。"""
		return len(self.folders)
