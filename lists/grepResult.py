# -*- coding: utf-8 -*-
#Falcon grep results list object
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import datetime
import os
import re
import wx
import logging
import win32api
import win32file
import pywintypes
import constants
import misc
import browsableObjects
import globalVars
import errorCodes
from win32com.shell import shell, shellcon

from .base import *
from .constants import *

ESCAPE_PATTERN=re.compile(r"([\\\+\.\{\}\(\)\[\]\^\$\-\|\/])")

class GrepResultList(FalconListBase):
	"""grep検索の結果を扱うリスト。"""
	def __init__(self):
		super().__init__()
		self.supportedSorts=[SORT_TYPE_BASENAME,SORT_TYPE_HITLINE,SORT_TYPE_PREVIEW,SORT_TYPE_HITCOUNT,SORT_TYPE_FILESIZE,SORT_TYPE_MODDATE,SORT_TYPE_ATTRIBUTES,SORT_TYPE_TYPESTRING]
		self.log=logging.getLogger("falcon.grepResultList")

	def Update(self):
		return self.Initialize(self.rootDirectory,self.searches,self.keyword,True)

	def Initialize(self,rootDirectory,searches="",keyword="",isRegularExpression=False,silent=False):
		"""与えられたファイル名のリストから、条件に一致する項目を抽出する。"""
		if isinstance(rootDirectory,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			self.results=rootDirectory
			return
		self.rootDirectory=rootDirectory
		self.searches=searches
		self.keyword_string=keyword
		#ワイルドカード (アスタリスクとクエスチョン)は、正規表現に置き換えしちゃう
		if not isRegularExpression:
			keyword=re.sub(ESCAPE_PATTERN,r"\\\1",keyword)
			keyword=keyword.replace("*",".*")
			keyword=keyword.replace("?",".")
		#end ワイルドカード置き換え
		self.keyword=re.compile(keyword)
		self.sortCursor=int(globalVars.app.config["SearchResultList"]["sorting"])
		self.sortDescending=int(globalVars.app.config["SearchResultList"]["descending"])
		if not silent: globalVars.app.say("%sの検索結果 %s から" % (keyword,rootDirectory,))
		self._initSearch()

	def RedoSearch(self):
		self._initSearch()

	def _initSearch(self):
		"""検索する前に準備する。"""
		self.finished=False
		self.results=[]
		self.log.debug("Getting grep search results for %s..." % self.keyword)
		self.searched_index=0#インデックスいくつまで検索したか

	def _performSearchStep(self,taskState):
		"""検索を1ステップ実行する。100県のヒットが出るまで検索するか、リストが終わるまで検索し、終わったら関数から抜ける。途中で EOL に当たったら、検索終了としてTrueを返し、そうでないときにFalseを帰す。また、表示関数に渡しやすいように、今回のステップでヒットした要素のリストも返す。スレッドからtaskStateを受け取っていて、キャンセルされたら hits を-1にセットして抜ける。"""
		ret_list=[]
		i=self.searched_index
		eol=False
		total_hits=0
		while(True):
			if taskState.canceled: return False, -1#途中でキャンセル
			path=self.searches[i]
			if path=="eol":#EOLで検索終了
				eol=True
				self.finished=True
				globalVars.app.PlaySound("complete.ogg")
				globalVars.app.say(_("検索終了、%(item)d件ヒットしました。") % {'item': len(self)})
				break
			#end EOL
			ext=path.split(".")[-1].lower()
			if misc.isDocumentExt(ext):
				fullpath=os.path.join(self.rootDirectory,path)
				content=misc.ExtractText(fullpath).split("\n")
				fileobj=None#複数ヒットでファイルオブジェクトを生成し続けないようにキャッシュする
				ln=1
				hitobjects=[]
				for	 elem in content:
					m=re.search(self.keyword,elem)
					if m:
						preview_start=m.start()-10
						if preview_start<0: preview_start=0
						preview=elem[preview_start:preview_start+20]
						if not fileobj:
							stat=os.stat(fullpath)
							mod=datetime.datetime.fromtimestamp(stat.st_mtime)
							creation=datetime.datetime.fromtimestamp(stat.st_ctime)
							ret, shfileinfo=shell.SHGetFileInfo(fullpath,0,shellcon.SHGFI_ICON|shellcon.SHGFI_TYPENAME)
							fileobj=browsableObjects.File()
							fileobj.Initialize(os.path.dirname(fullpath),os.path.basename(fullpath),fullpath,stat.st_size,mod,win32file.GetFileAttributes(fullpath),shfileinfo[4],creation,win32api.GetShortPathName(fullpath))
						#end make fileobj
						obj=browsableObjects.GrepItem()
						obj.Initialize(ln,preview,fileobj)
						hitobjects.append(obj)
					#end ヒット
					ln+=1
				#end 行数ごとに検索
				if len(hitobjects)>0:#このファイルの中でヒットがあった
					total_hits+=len(hitobjects)
					for elem in hitobjects:
						hits=len(hitobjects)
						elem.SetHitCount(hits)
					#end 最終的なヒットカウントを設定
					self.results.extend(hitobjects)
					ret_list.extend(hitobjects)
				#end このファイルでヒットがあった
			#end 対応している拡張子
			if total_hits>=100:
				self.searched_index=i+1#次の位置をキャッシュ
				break
			#end 100県検索
			i+=1
			if i>=len(self.searches):#検索は終わってないが、ファイルリスト取得が追いついてない
				self.searched_index=len(self.searches)
				break
			#end リストが追いついてない
		#end 検索ループ
		return eol,ret_list

	def GetKeywordString(self):
		return self.keyword_string

	def GetColumns(self):
		"""このリストのカラム情報を返す。"""
		return {
			_("ファイル名"):wx.LIST_FORMAT_LEFT,
			_("行"): wx.LIST_FORMAT_RIGHT,
			_("プレビュー"): wx.LIST_FORMAT_LEFT,
			_("ヒット件数"): wx.LIST_FORMAT_RIGHT,
			_("サイズ"):wx.LIST_FORMAT_RIGHT,
			_("更新"):wx.LIST_FORMAT_LEFT,
			_("属性"):wx.LIST_FORMAT_LEFT,
			_("種類"):wx.LIST_FORMAT_LEFT
		}

	def GetItems(self):
		"""リストの中身を文字列タプルで取得する。"""
		lst=[]
		for elem in self.results:
			lst.append(elem.GetListTuple())
		return lst

	def GetItemPaths(self):
		"""リストの中身をパスのリストで取得する。"""
		lst=[]
		for elem in self.results:
			lst.append(elem.fullpath)
		return lst

	def GetItemNames(self):
		"""リストの中身をファイル名のリストで取得する。"""
		lst=[]
		for elem in self.results:
			lst.append(elem.basename)
		return lst

	def GetElement(self,index):
		"""インデックスを指定して、対応するリスト内のオブジェクトを返す。"""
		return self.results[index]

	def _sort(self,attrib, descending):
		"""指定した要素で、リストを並べ替える。"""
		self.log.debug("Begin sorting (attrib %s, descending %s)" % (attrib, descending))
		t=misc.Timer()
		f=self._getSortFunction(attrib)
		self.results.sort(key=f, reverse=(descending==1))
		self.log.debug("Finished sorting (%f seconds)" % t.elapsed)

	def GetAttributeCheckState(self):
		"""このリストに入っているファイルを1個ずつとって、対応するファイルの属性値を取得していく。各属性に対して、リスト内の全てのファイルが持っていれば ATTRIB_FULL_CHECKED を帰す。一部のファイルが持っていれば、 ATTRIB_HALF_CHECKED を帰す。どのファイルも持っていなければ、 ATTRIB_NOT_CHECKED を帰す。このデータを、リストにして帰す。"""
		found=[0,0,0,0]#各属性を見つけた個数
		ret=[constants.NOT_CHECKED, constants.NOT_CHECKED, constants.NOT_CHECKED, constants.NOT_CHECKED]#帰す値
		for elem in self:
			attrib=elem.attributes
			if attrib&win32file.FILE_ATTRIBUTE_READONLY:
				found[READONLY]+=1
				ret[READONLY]=constants.HALF_CHECKED
			#end readonly
			if attrib&win32file.FILE_ATTRIBUTE_HIDDEN:
				found[HIDDEN]+=1
				ret[HIDDEN]=constants.HALF_CHECKED
			#end hidden
			if attrib&win32file.FILE_ATTRIBUTE_SYSTEM:
				found[SYSTEM]+=1
				ret[SYSTEM]=constants.HALF_CHECKED
			#end system
			if attrib&win32file.FILE_ATTRIBUTE_ARCHIVE:
				found[ARCHIVE]+=1
				ret[ARCHIVE]=constants.HALF_CHECKED
			#end system
		#end for
		l=len(self)
		if found[READONLY]==l: ret[READONLY]=constants.FULL_CHECKED
		if found[HIDDEN]==l: ret[HIDDEN]=constants.FULL_CHECKED
		if found[SYSTEM]==l: ret[SYSTEM]=constants.FULL_CHECKED
		if found[ARCHIVE]==l: ret[ARCHIVE]=constants.FULL_CHECKED
		return ret

	def GetFinishedStatus(self):
		return self.finished

	def __iter__(self):
		return self.results.__iter__()

	def __len__(self):
		return len(self.results)
