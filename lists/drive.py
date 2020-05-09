# -*- coding: utf-8 -*-
#Falcon drive list object
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import win32api
import win32file
import win32wnet
import socket

import pywintypes
import constants
import misc
import browsableObjects
import globalVars
import errorCodes

from simpleDialog import dialog
from .base import *
from .constants import *
from win32com.shell import shell, shellcon

class DriveList(FalconListBase):
	"""ドライブの一覧を扱うクラス。"""
	def __init__(self):
		super().__init__()
		self.supportedSorts=[SORT_TYPE_BASENAME,SORT_TYPE_DRIVELETTER,SORT_TYPE_FREESPACE,SORT_TYPE_TOTALSPACE, SORT_TYPE_TYPESTRING]
		self.columns={
			_("ラベル"):wx.LIST_FORMAT_LEFT,
			_("レター"):wx.LIST_FORMAT_LEFT,
			_("空き"):wx.LIST_FORMAT_RIGHT,
			_("合計"):wx.LIST_FORMAT_RIGHT,
			_("種類"):wx.LIST_FORMAT_LEFT
		}
		self.drives=[]
		self.unusableDrives=[]
		self.networkResources=[]
		self.lists=[self.drives,self.unusableDrives,self.networkResources]

	def Update(self):
		return self.Initialize(None,True)

	def Initialize(self,lst=None,silent=False):
		"""ドライブ情報を取得し、リストを初期化する。"""
		self.sortCursor=int(globalVars.app.config["DriveList"]["sorting"])
		self.sortDescending=int(globalVars.app.config["DriveList"]["descending"])
		self.log.debug("Getting drives list...")
		self.rootDirectory=""
		t=misc.Timer()
		if isinstance(lst,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			self._copyFromList(lst)
			return errorCodes.OK
		#end copy

		if not silent:
			globalVars.app.say(_("ドライブ洗濯"))
		drv=win32api.GetLogicalDrives()
		check=1
		for i in range(26):
			if drv&check: self.Append(i)#ドライブ検出
			check<<=1
		#end ドライブ25個分調べる

		#ネットワークリソースの追加
		self._GetNetworkResources()

		self.log.debug("Drives list created in %d seconds." % t.elapsed)
		self.log.debug(str(len(self.drives))+" drives,"+str(len(self.unusableDrives))+" unusableDrives and "+str(len(self.networkResources))+" networkResources found.")
		self.ApplySort()
		return errorCodes.OK

	def _copyFromList(self,lst):
		self.log.debug("Copying from list...")
		for elem in lst:
			if isinstance(elem,browsableObjects.NetworkResource):
				self.networkResources.append(elem)
			elif elem.total>=0:
				self.drives.append(elem)
			else:
				self.unusableDrives.append(elem)
			#end ファイルかフォルダか
		#end for
	#end _copyFromList

	def _GetNetworkResources(self):
		self.log.debug("Getting networkResource list...")
		try:
			h=win32wnet.WNetOpenEnum(5,1,0,None)
				#5=RESOURCE_CONTEXT
				#1=RESOURCETYPE_DISK
			lst=win32wnet.WNetEnumResource(h,64)	#65以上の指定不可
			win32wnet.WNetCloseEnum(h);
		except win32net.error as er:
			dialog(_("エラー"), _("ネットワーク上のリソース一覧を取得できませんでした(%(error)s)") % {"error": str(er)})
			return
		#end 情報取得失敗
		lst.pop(0)	#先頭はドライブではない者が入るので省く
		for l in lst:
			ret, shfileinfo=shell.SHGetFileInfo(l.lpRemoteName,0,shellcon.SHGFI_ICON)
			s=browsableObjects.NetworkResource()
			s.Initialize(l.lpRemoteName[2:],l.lpRemoteName,socket.getaddrinfo(l.lpRemoteName[2:],None)[0][4][0],shfileinfo[0])
			self.networkResources.append(s)
		#end 追加ループ

	def Append(self,index):
		d=GetDriveObject(index)
		if d.total==-1:
			self.unusableDrives.append(d)
		else:
			self.drives.append(d)
		#end どっちに追加するか？

def GetDriveObject(index):
	"""ドライブ情報を調べて、browsableObjectsで返す。Aドライブが0、Zドライブが25。"""
	letter=chr(index+65)
	path=letter+":\\"
	type=win32file.GetDriveType(path)
	f=-1
	t=-1
	n=""
	try:
		freeSpace=win32api.GetDiskFreeSpaceEx(path)
		f=freeSpace[0]
		t=freeSpace[1]
		volumeInfo=win32api.GetVolumeInformation(path)
		n=volumeInfo[0]
	except pywintypes.error as err:
		pass
	#エラーは無視
	d=browsableObjects.Drive()
	ret, shfileinfo=shell.SHGetFileInfo(letter+":\\",0,shellcon.SHGFI_ICON)
	d.Initialize(letter,f,t,type,n,shfileinfo[0])
	return d
