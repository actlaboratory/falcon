# -*- coding: utf-8 -*-
#Falcon searchResultBase Function
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
import globalVars

from win32com.shell import shell, shellcon

from .fileListBase import *

ESCAPE_PATTERN=re.compile(r"([\\\+\.\{\}\(\)\[\]\^\$\-\|\/])")

class SearchResultBase(FileListBase):
	def __init__(self):
		super().__init__()

	def _performSearchStep(self,taskState):
		"""検索を1ステップ実行する。100県のファイルがヒットするか、リストが終わるまで検索し、終わったら関数から抜ける。途中で EOL に当たったら、検索終了としてTrueを返し、そうでないときにFalseを帰す。また、表示関数に渡しやすいように、今回のステップでヒットした要素のリストも返す。"""
		ret_list=[]
		i=self.searched_index
		hit=0
		while(True):
			if taskState.canceled: return False, -1#途中でキャンセル
			path=self.searches[i]
			if path=="eol":#EOLで検索終了
				self.finished=True
				globalVars.app.PlaySound("complete.ogg")
				globalVars.app.say(_("検索終了、%(item)d件ヒットしました。") % {'item': len(self)})
				return True,ret_list
			#end EOL
			result=self.HitTest(path,ret_list)
			hit+=result
			if hit==100:
				self.searched_index=i+1#次の位置をキャッシュ
				break
			#end 100県ヒット
			i+=1
			if i>=len(self.searches):#検索は終わってないが、ファイルリスト取得が追いついてない
				self.searched_index=len(self.searches)
				break
			#end リストが追いついてない
		#end 検索ループ
		return False,ret_list

	def GetFinishedStatus(self):
		"""
			workerThreadTaskでの検索処理が終わっているならTrue
			画面上のlistCtrlへの追加完了とは一致しない
		"""
		return self.finished

	def GetKeywordString(self):
		return self.keyword_string

	def _initKeyword(self,keyword,isRegularExpression,silent):
		self.keyword_string=keyword
		#ワイルドカード (アスタリスクとクエスチョン)は、正規表現に置き換えしちゃう
		if not isRegularExpression:
			keyword=re.sub(ESCAPE_PATTERN,r"\\\1",keyword)
			keyword=keyword.replace("*",".*")
			keyword=keyword.replace("?",".")
		#end ワイルドカード置き換え
		self.keyword=re.compile(keyword)
		if not silent: globalVars.app.say("%sの検索結果 %s から" % (keyword,self.rootDirectory,))

	def _initSearch(self):
		"""検索する前に準備する。"""
		self.finished=False
		for l in self.lists:
			l.clear()
		self.log.debug("Getting search results for %s..." % self.keyword)
		self.searched_index=0#インデックスいくつまで検索したか

	def _MakeObject(self,objType,fullpath,isDir=False):
		stat=os.stat(fullpath)
		ret, shfileinfo=shell.SHGetFileInfo(fullpath,0,shellcon.SHGFI_ICON | shellcon.SHGFI_TYPENAME)
		obj=objType()
		if isDir:
			size=-1
		else:
			size=stat.st_size
		obj.Initialize(
			os.path.dirname(fullpath),						#directory
			os.path.basename(fullpath),						#basename
			fullpath,
			size,									#size
			datetime.datetime.fromtimestamp(stat.st_mtime),	#modDate
			win32file.GetFileAttributes(fullpath),			#attributes
			shfileinfo[4],									#typeString
			datetime.datetime.fromtimestamp(stat.st_ctime),	#creationDate
			win32api.GetShortPathName(fullpath),			#shortName
			shfileinfo[0]									#hIcon
		)
		return obj

	def Update(self):
		return self.Initialize(self.rootDirectory,self.searches,self.keyword,True)

	def RedoSearch(self):
		self._initSearch()
