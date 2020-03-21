# -*- coding: utf-8 -*-
#Falcon networkDevice list object
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import logging
import constants
import misc
import browsableObjects
import globalVars
import errorCodes

import win32wnet
import socket

from .base import *
from .constants import *

class NetworkDeviceList(FalconListBase):
	"""ネットワーク上のリソースを扱うリスト。"""
	def __init__(self):
		super().__init__()
		self.log=logging.getLogger("falcon.networkDeviceList")

	def Update(self):
		return self.Initialize(True)

	def Initialize(self,lst,silent=False):
		"""ネットワーク上からデバイス一覧を取得する。情報が取得できなかった場合、errorCodes.OK以外が返る。"""
		t=misc.Timer()
		self.devices=[]

		if isinstance(lst,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			self.devices=lst
			return
		#end copy

		if not silent:
			globalVars.app.say(_("ネットワークデバイスリスト"))
		self.log.debug("Getting device list...")
		try:
			h=win32wnet.WNetOpenEnum(5,1,0,None)
				#5=RESOURCE_CONTEXT
				#1=RESOURCETYPE_DISK
			lst=win32wnet.WNetEnumResource(h,64)	#65以上の指定不可
			win32wnet.WNetCloseEnum(h);
		except win32net.error as er:
			dialog(_("エラー"), _("ネットワーク上のリソース一覧を取得できませんでした(%(error)s)") % {"error": str(er)})
			return False
		#end 情報取得失敗
		lst.pop(0)	#先頭はドライブではない者が入るので省く
		for elem in lst:
			s=browsableObjects.NetworkResource()
			s.Initialize(elem.lpLocalName,l.lpRemoteName,socket.getaddrinfo(l.lpRemoteName[2:],None)[0][4][0])
			self.devices.append(s)
		#end 追加ループ
		self.log.debug("networkDevice list created in %d milliseconds." % t.elapsed)
		self.log.debug(str(len(self.devices))+" objects found.")
		return True

	def GetColumns(self):
		"""このリストのカラム情報を返す。"""
		return {_("名前"):wx.LIST_FORMAT_LEFT,_("リモートネーム"):wx.LIST_FORMAT_LEFT,_("IPアドレス"):wx.LIST_FORMAT_LEFT}

	def GetItems(self):
		"""リストの中身を文字列タプルで取得する。"""
		lst=[]
		for elem in self.devices:
			lst.append(elem.GetListTuple())
		return lst

	def GetItemPaths(self):
		"""リストの中身をフルパスのリストで取得する。"""
		lst=[]
		for elem in self.devices:
			lst.append(elem.fullpath)
		return lst

	def GetElement(self,index):
		"""インデックスを指定して、対応するリスト内のオブジェクトを返す。"""
		return self.devices[index]

	def GetItemNames(self):
		"""リストの中身をリストで取得する。"""
		lst=[]
		for elem in self.devices:
			lst.append(elem.basename)
		return lst
