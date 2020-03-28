# -*- coding: utf-8 -*-
#Falcon drive list object
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
from simpleDialog import dialog
from .base import *
from .constants import *

class DriveList(FalconListBase):
	"""ドライブの一覧を扱うクラス。"""
	def __init__(self):
		super().__init__()
		self.supportedSorts=[SORT_TYPE_BASENAME,SORT_TYPE_DRIVELETTER,SORT_TYPE_FREESPACE,SORT_TYPE_TOTALSPACE, SORT_TYPE_TYPESTRING]
		self.log=logging.getLogger("falcon.driveList")

	def Update(self):
		return self.Initialize(None,True)

	def Initialize(self,lst,silent=False):
		"""ドライブ情報を取得し、リストを初期化する。"""
		self.sortCursor=int(globalVars.app.config["DriveList"]["sorting"])
		self.sortDescending=int(globalVars.app.config["DriveList"]["descending"])
		self.log.debug("Getting drives list...")
		self.rootDirectory=""
		t=misc.Timer()
		self.drives=[]
		self.unusableDrives=[]
		if isinstance(lst,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			self.drives=lst
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
		self.log.debug("Drives list created in %d seconds." % t.elapsed)
		self.log.debug(str(len(self.drives))+" drives found.")
		self.ApplySort()
		return errorCodes.OK

	def GetColumns(self):
		"""このリストのカラム情報を返す。"""
		return {
			_("ラベル"):wx.LIST_FORMAT_LEFT,
			_("レター"):wx.LIST_FORMAT_LEFT,
			_("空き"):wx.LIST_FORMAT_RIGHT,
			_("合計"):wx.LIST_FORMAT_RIGHT,
			_("種類"):wx.LIST_FORMAT_LEFT
		}

	def Append(self,index):
		"""ドライブ情報を調べて、リストに追加する。Aドライブが0、Zドライブが25。"""
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
		d.Initialize(letter,f,t,type,n)
		if t==-1:
			self.unusableDrives.append(d)
		else:
			self.drives.append(d)
		#end どっちに追加するか？

	def GetItems(self):
		"""リストの中身を取得する。"""
		lst=[]
		for elem in self.drives:
			lst.append(elem.GetListTuple())
		for elem in self.unusableDrives:
			lst.append(elem.GetListTuple())
		return lst

	def GetItemPaths(self):
		"""リスト内のドライブのパス一覧を取得する。"""
		lst=[]
		for elem in self.drives:
			lst.append(elem.fullpath)
		for elem in self.unusableDrives:
			lst.append(elem.fullpath)
		return lst

	def GetElement(self,index):
		"""インデックスを指定して、対応するリスト内のオブジェクトを返す。"""
		return self.drives[index] if index<len(self.drives) else self.unusableDrives[index-len(self.drives)]

	def _sort(self,attrib, descending):
		"""指定した要素で、リストを並べ替える。"""
		self.log.debug("Begin sorting (attrib %s, descending %s)" % (attrib, descending))
		t=misc.Timer()
		f=self._getSortFunction(attrib)
		self.drives.sort(key=f, reverse=(descending==1))
		self.log.debug("Finished sorting (%f seconds)" % t.elapsed)

	def __iter__(self):
		return self.drives.__iter__()

	def __len__(self):
		return len(self.drives)+len(self.unusableDrives)
