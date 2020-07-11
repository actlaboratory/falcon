# -*- coding: utf-8 -*-
#Falcon grep results list object
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import os
import re
import wx

import browsableObjects
import errorCodes
import misc

from .searchResultBase import *
from .constants import *

class GrepResultList(SearchResultBase):
	"""grep検索の結果を扱うリスト。"""
	def __init__(self):
		super().__init__()
		self.supportedSorts=[SORT_TYPE_BASENAME,SORT_TYPE_HITLINE,SORT_TYPE_PREVIEW,SORT_TYPE_HITCOUNT,SORT_TYPE_FILESIZE,SORT_TYPE_MODDATE,SORT_TYPE_ATTRIBUTES,SORT_TYPE_TYPESTRING]
		self.columns={
			_("ファイル名"):wx.LIST_FORMAT_LEFT,
			_("行"): wx.LIST_FORMAT_RIGHT,
			_("プレビュー"): wx.LIST_FORMAT_LEFT,
			_("ヒット件数"): wx.LIST_FORMAT_RIGHT,
			_("サイズ"):wx.LIST_FORMAT_RIGHT,
			_("更新"):wx.LIST_FORMAT_LEFT,
			_("属性"):wx.LIST_FORMAT_LEFT,
			_("種類"):wx.LIST_FORMAT_LEFT
		}
		self.results=[]
		self.lists=[self.results]


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
		if misc.isDocumentExt(path.split(".")[-1]):
			fullpath=os.path.join(self.rootDirectory,path)
			content=misc.ExtractText(fullpath).split("\n")
			fileobj=None#複数ヒットでファイルオブジェクトを生成し続けないようにキャッシュする
			ln=1
			hitobjects=[]
			for	 elem in content:
				m=re.search(self.keyword,elem)
				if m:
					preview_start=max(0,m.start()-10)
					preview=elem[preview_start:preview_start+25]
					if not fileobj:
						fileobj=self._MakeObject(browsableObjects.File,fullpath)
					obj=browsableObjects.GrepItem()
					obj.Initialize(ln,preview,fileobj)
					hitobjects.append(obj)
				#end ヒット
				ln+=1
			#end 行数ごとに検索
			for elem in hitobjects:
				hits=len(hitobjects)
				elem.SetHitCount(hits)
			#end 最終的なヒットカウントを設定
			self.results.extend(hitobjects)
			ret_list.extend(hitobjects)
			return len(hitobjects)
		#end 対応している拡張子
		return 0
