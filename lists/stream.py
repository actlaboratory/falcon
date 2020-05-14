# -*- coding: utf-8 -*-
#Falcon stream list object
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import win32file
import misc
import browsableObjects
import globalVars
import errorCodes

from simpleDialog import *

from .base import *
from .constants import *


class StreamList(FalconListBase):
	"""NTFS 副ストリームを扱うリスト。"""
	def __init__(self):
		super().__init__()
		self.supportedSorts=[SORT_TYPE_BASENAME,SORT_TYPE_FILESIZE]
		self.columns={_("ストリーム名"):wx.LIST_FORMAT_LEFT,_("サイズ"):wx.LIST_FORMAT_RIGHT}
		self.streams=[]
		self.lists=[self.streams]

	def Update(self):
		return self.Initialize(self.rootDirectory,True)

	def Initialize(self,file,silent=False):
		"""ファイル名から副ストリーム情報を取得し、リストを初期化する。入力は絶対パスでなければならない。情報が取得できなかった場合、errorCodes.OK以外が返る。。"""
		t=misc.Timer()
		if isinstance(file,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			self.streams=file
			self.lists=[self.streams]
			return
		#end copy

		self.streams.clear()
		file_spl=file.split("\\")
		self.rootDirectory=file
		level=len(file_spl)
		if not silent:
			globalVars.app.say("%s%d %s" % (file[0],level,file_spl[level-1]))
		self.log.debug("Getting stream list for %s..." % file)
		try:
			lst=win32file.FindStreams(file)
		except win32file.error as er:
			dialog(_("エラー"), _("NTFS 副ストリーム情報を取得できませんでした(%(error)s)") % {"error": str(er)})
			return False
		#end 情報取得失敗
		lst=lst[1:]	#先頭はファイル本体なので省く
		for elem in lst:
			s=browsableObjects.Stream()
			s.Initialize(file,elem[1][1:-6],file+elem[1][0:-6],elem[0])
			self.streams.append(s)
		#end 追加ループ
		self.log.debug("stream list created in %d milliseconds." % t.elapsed)
		self.log.debug(str(len(self.streams))+" objects found.")
		if self.sortCursor!=0 or self.sortDescending!=0:
			self.log.debug("Triggering sorting")
			self.ApplySort()
		#end ソートが必要ならソート
		return errorCodes.OK
