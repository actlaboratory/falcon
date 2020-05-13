# -*- coding: utf-8 -*-
#Falcon search results list object
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import datetime
import os
import re
import wx
import win32api
import win32file
import constants
import misc
import browsableObjects
import globalVars
import errorCodes
from win32com.shell import shell, shellcon

from .base import *
from .constants import *

ESCAPE_PATTERN=re.compile(r"([\\\+\.\{\}\(\)\[\]\^\$\-\|\/])")

class SearchResultList(FalconListBase):
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

	def Update(self):
		return self.Initialize(self.rootDirectory,self.searches,self.keyword,True)

	def Initialize(self,rootDirectory,searches="",keyword="",isRegularExpression=False,silent=False):
		"""与えられたファイル名のリストから、条件に一致する項目を抽出する。"""
		if isinstance(rootDirectory,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			for elem in rootDirectory:
				if type(elem) is browsableObjects.Folder:
					self.folders.append(elem)
				else:
					self.files.append(elem)
				#end ファイルかフォルダか
			#end for
			return errorCodes.OK
		self.folders.clear()
		self.files.clear()
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
		self.folders=[]
		self.files=[]
		self.lists=[self.folders,self.files]
		self.log.debug("Getting search results for %s..." % self.keyword)
		self.searched_index=0#インデックスいくつまで検索したか

	def _performSearchStep(self,taskState):
		"""検索を1ステップ実行する。100県のファイルがヒットするか、リストが終わるまで検索し、終わったら関数から抜ける。途中で EOL に当たったら、検索終了としてTrueを返し、そうでないときにFalseを帰す。また、表示関数に渡しやすいように、今回のステップでヒットした要素のリストも返す。"""
		ret_list=[]
		i=self.searched_index
		eol=False
		hit=0
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
			if re.search(self.keyword,path):
				fullpath=os.path.join(self.rootDirectory,path)
				stat=os.stat(fullpath)
				mod=datetime.datetime.fromtimestamp(stat.st_mtime)
				creation=datetime.datetime.fromtimestamp(stat.st_ctime)
				ret, shfileinfo=shell.SHGetFileInfo(fullpath,0,shellcon.SHGFI_ICON|shellcon.SHGFI_TYPENAME)
				if os.path.isfile(fullpath):
					f=browsableObjects.File()
					f.Initialize(os.path.dirname(fullpath),os.path.basename(fullpath),fullpath,stat.st_size,mod,win32file.GetFileAttributes(fullpath),shfileinfo[4],creation,win32api.GetShortPathName(fullpath))
					self.files.append(f)
					ret_list.append(f)
				else:
					f=browsableObjects.Folder()
					f.Initialize(os.path.dirname(fullpath),os.path.basename(fullpath),fullpath,-1,mod,win32file.GetFileAttributes(fullpath),shfileinfo[4],creation,win32api.GetShortPathName(fullpath))
					self.folders.append(f)
					ret_list.append(f)
				#end ファイルかフォルダか
				hit+=1
				if hit==100:
					self.searched_index=i+1#次の位置をキャッシュ
					break
				#end 100県ヒット
			#end 検索ヒットか
			i+=1
			if i>=len(self.searches):#検索は終わってないが、ファイルリスト取得が追いついてない
				self.searched_index=len(self.searches)
				break
			#end リストが追いついてない
		#end 検索ループ
		return eol,ret_list

	def GetKeywordString(self):
		return self.keyword_string

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

	def GetFolderFileNumber(self):
		return len(self.folders), len(self.files)

	def GetTopFileIndex(self):
		"""先頭ファイルのインデックス番号を返す。"""
		return len(self.folders)
