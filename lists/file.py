# -*- coding: utf-8 -*-
#Falcon file list object
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import os
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

class FileList(FalconListBase):
	"""ファイルとフォルダの一覧を扱うリスト。"""
	def __init__(self):
		super().__init__()
		self.supportedSorts=[SORT_TYPE_BASENAME,SORT_TYPE_FILESIZE,SORT_TYPE_MODDATE,SORT_TYPE_ATTRIBUTES,SORT_TYPE_TYPESTRING]
		self.log=logging.getLogger("falcon.fileList")

	def Update(self):
		return self.Initialize(self.rootDirectory,True)

	def Initialize(self,dir,silent=False):
		"""ディレクトリからファイル情報を取得し、リストを初期化する。入力は絶対パスでなければならない。情報が取得できなかった場合、errorCodes.OK以外が返る。silentがTrueなら読み上げは行われない。"""
		self.sortCursor=int(globalVars.app.config["FileList"]["sorting"])
		self.sortDescending=int(globalVars.app.config["FileList"]["descending"])
		self.files=[]
		self.folders=[]
		if isinstance(dir,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			self._copyFromList(dir)
			return errorCodes.OK
		#end copy
		dir=dir.rstrip("\\")
		dir_spl=dir.split("\\")
		level=len(dir_spl)
		if not silent:
			globalVars.app.say("%s%d %s" % (dir[0],level,dir_spl[level-1]))
		self.rootDirectory=dir
		self.log.debug("Getting file list for %s..." % self.rootDirectory)
		t=misc.Timer()
		try:
			lst=win32api.FindFiles(dir+"\\*")
		except pywintypes.error as err:
			self.log.error("Cannot open the directory! {0}".format(err))
			if err.winerror==5:
				return errorCodes.ACCESS_DENIED
			dialog(_("エラー"), _("フォルダを開くことができませんでした(%(error)s)") % {"error": str(err)})
			return errorCodes.FATAL
		#end except
		if "\\" in self.rootDirectory:		#ルート以外では余計な.と..がが一番上に入っている
			del lst[0:2]
		if len(lst)==0:
			self.log.debug("Blank folder.")
			return errorCodes.OK
		#end 空のフォルダだったらさっさと帰る
		for elem in lst:
			fullpath=dir+"\\"+elem[8]
			ret, shfileinfo=shell.SHGetFileInfo(fullpath,0,shellcon.SHGFI_ICON|shellcon.SHGFI_TYPENAME)
			if os.path.isfile(fullpath):
				f=browsableObjects.File()
				f.Initialize(dir,elem[8],fullpath,(elem[4]<<32)+elem[5], elem[3], elem[0], shfileinfo[4],elem[1],elem[9])
				self.files.append(f)
			else:
				f=browsableObjects.Folder()
				f.Initialize(dir,elem[8],fullpath,-1,elem[3], elem[0], shfileinfo[4],elem[1],elem[9])
				self.folders.append(f)
			#end どっちについかするか？
		#end 追加ループ
		self.log.debug("File list created in %f seconds." % t.elapsed)
		self.log.debug(str(len(self.folders))+" directories and "+str(len(self.files))+" files found.")
		if self.sortCursor!=0:
			self.log.debug("Triggering sorting")
			self.ApplySort()
		#end ソートが必要ならソート
		return errorCodes.OK

	def _copyFromList(self,lst):
		self.log.debug("Copying from file list...")
		for elem in lst:
			if isinstance(elem,browsableObjects.File):
				self.files.append(elem)
			elif isinstance(elem,browsableObjects.Folder):
				self.folders.append(elem)
			#end ファイルかフォルダか
		#end for
	#end _copyFromList

	def GetColumns(self):
		"""このリストのカラム情報を返す。"""
		return {
			_("ファイル名"):wx.LIST_FORMAT_LEFT,
			_("サイズ"):wx.LIST_FORMAT_RIGHT,
			_("更新"):wx.LIST_FORMAT_LEFT,
			_("属性"):wx.LIST_FORMAT_LEFT,
			_("種類"):wx.LIST_FORMAT_LEFT
		}

	def GetItems(self):
		"""リストの中身を文字列タプルで取得する。フォルダが上にくる。"""
		lst=[]
		for elem in self.folders:
			lst.append(elem.GetListTuple())
		for elem in self.files:
			lst.append(elem.GetListTuple())
		return lst

	def GetItemPaths(self):
		"""リストの中身をパスのリストで取得する。フォルダが上にくる。"""
		lst=[]
		for elem in self.folders:
			lst.append(elem.fullpath)
		for elem in self.files:
			lst.append(elem.fullpath)
		return lst

	def GetItemNames(self):
		"""リストの中身をファイル名のリストで取得する。フォルダが上にくる。"""
		lst=[]
		for elem in self.folders:
			lst.append(elem.basename)
		for elem in self.files:
			lst.append(elem.basename)
		return lst

	def GetElement(self,index):
		"""インデックスを指定して、対応するリスト内のオブジェクトを返す。"""
		return self.folders[index] if index<len(self.folders) else self.files[index-len(self.folders)]

	def GetTopFileIndex(self):
		"""先頭ファイルのインデックス番号を返す。"""
		return len(self.folders)

	def _sort(self,attrib, descending):
		"""指定した要素で、リストを並べ替える。"""
		self.log.debug("Begin sorting (attrib %s, descending %s)" % (attrib, descending))
		t=misc.Timer()
		f=self._getSortFunction(attrib)
		self.files.sort(key=f, reverse=(descending==1))
		self.folders.sort(key=f, reverse=(descending==1))
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

	def __iter__(self):
		lst=self.folders+self.files
		return lst.__iter__()

	def __len__(self):
		return len(self.folders)+len(self.files)
