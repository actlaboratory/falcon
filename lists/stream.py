# -*- coding: utf-8 -*-
#Falcon stream list object
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

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

from .base import *
from .constants import *

class StreamList(FalconListBase):
	"""NTFS 副ストリームを扱うリスト。"""
	def __init__(self):
		super().__init__()
		self.log=logging.getLogger("falcon.streamList")

	def Update(self):
		return self.Initialize(self.rootDirectory,True)

	def Initialize(self,file,silent=False):
		"""ファイル名から副ストリーム情報を取得し、リストを初期化する。入力は絶対パスでなければならない。情報が取得できなかった場合、errorCodes.OK以外が返る。。"""
		t=misc.Timer()
		self.streams=[]

		if isinstance(file,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			self.streams=file
			return
		#end copy

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
		for elem in lst:
			fullpath=file+elem[1]
			s=browsableObjects.Stream()
			s.Initialize(file,elem[1],fullpath,elem[0])
			self.streams.append(s)
		#end 追加ループ
		self.log.debug("stream list created in %d milliseconds." % t.elapsed)
		self.log.debug(str(len(self.streams))+" objects found.")
		return True

	def GetColumns(self):
		"""このリストのカラム情報を返す。"""
		return {_("ストリーム名"):wx.LIST_FORMAT_LEFT,_("サイズ"):wx.LIST_FORMAT_RIGHT}

	def GetItems(self):
		"""リストの中身を文字列タプルで取得する。"""
		lst=[]
		for elem in self.streams:
			lst.append(elem.GetListTuple())
		return lst

	def GetItemPaths(self):
		"""リストの中身をフルパスのリストで取得する。"""
		lst=[]
		for elem in self.streams:
			lst.append(elem.fullpath)
		return lst

	def GetElement(self,index):
		"""インデックスを指定して、対応するリスト内のオブジェクトを返す。"""
		return self.streams[index]

	def GetItemPaths(self):
		"""リストの中身をパスのリストで取得する。フォルダが上にくる。"""
		lst=[]
		for elem in self.streams:
			lst.append(elem.fullpath)
		return lst

	def GetItemNames(self):
		"""リストの中身をファイル名のリストで取得する。フォルダが上にくる。"""
		lst=[]
		for elem in self.streams:
			lst.append(elem.basename)
		return lst
