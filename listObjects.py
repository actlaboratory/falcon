# -*- coding: utf-8 -*-
#Falcon generic list management
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import os
import logging
import win32api
import win32file
import pywintypes
import misc
import browsableObjects
class FalconListBase(object):
	"""全てのリストに共通する基本クラス。"""
	def __init__(self):
		pass

	def __del__(self):
		pass

class FileList(FalconListBase):
	"""ファイルとフォルダの一覧を扱うリスト。"""
	def Initialize(self,dir):
		"""ディレクトリからファイル情報を取得し、リストを初期化する。入力は絶対パスでなければならない。情報が取得できなかった場合、Falseが帰る。"""
		self.log=logging.getLogger("falcon.fileList")
		self.rootDirectory=dir
		self.log.debug("Getting file list for %s..." % self.rootDirectory)
		t=misc.Timer()
		try:
			lst=win32api.FindFiles(dir+"\\*")
		except pywintypes.error as err:
			self.log.error("Cannot open the directory! {0}".format(err))
			return False
		#end except
		self.files=[]
		self.folders=[]
		del lst[0:2]
		for elem in lst:
			fullpath=dir+"\\"+elem[8]
			if os.path.isfile(fullpath):
				f=browsableObjects.File()
				f.Initialize(dir,elem[8],fullpath,(elem[4]<<32)+elem[5], elem[3], elem[0], "undefined")
				self.files.append(f)
			else:
				f=browsableObjects.Folder()
				f.Initialize(dir,elem[8],fullpath,0,elem[3], elem[0], "undefined")
				self.folders.append(f)
			#end どっちについかするか？
		#end 追加ループ
		self.log.debug("File list created in %d milliseconds." % t.elapsed)

	def GetItems(self):
		"""リストの中身を取得する。フォルダが上にくる。"""
		lst=[]
		for elem in self.folders:
			lst.append(elem.GetListTuple())
		for elem in self.files:
			lst.append(elem.GetListTuple())
		return lst

	def GetElement(self,index):
		"""インデックスを指定して、対応するリスト内のオブジェクトを返す。"""
		return self.folders[index] if index<len(self.folders) else self.files[index-len(self.folders)]

class DriveList(FalconListBase):
	"""ドライブの一覧を扱うクラス。"""
	def Initialize(self):
		"""ドライブ情報を取得し、リストを初期化する。入力は絶対パスでなければならない。"""
		self.log=logging.getLogger("falcon.driveList")
		self.log.debug("Getting drives list...")
		t=misc.Timer()
		self.drives=[]
		drv=win32api.GetLogicalDrives()
		check=1
		for i in range(26):
			if drv&check: self.Append(i)#ドライブ検出
			check<<=1
		#end ドライブ25個分調べる
		self.log.debug("Drives list created in %d seconds." % t.elapsed)

	def Append(self,index):
		"""ドライブ情報を調べて、リストに追加する。Aドライブが0、Zドライブが25。"""
		letter=chr(index+65)
		path=letter+":\\"
		type=win32file.GetDriveType(path)
		freeSpace=win32api.GetDiskFreeSpaceEx(path)
		volumeInfo=win32api.GetVolumeInformation(path)
		d=browsableObjects.Drive()
		d.Initialize(letter, freeSpace[0], freeSpace[1], type, volumeInfo[0])
		self.drives.append(d)

	def GetItems(self):
		"""リストの中身を取得する。フォルダが上にくる。"""
		lst=[]
		for elem in self.drives:
			lst.append(elem.GetListTuple())
		return lst
