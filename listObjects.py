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
import globalVars
from simpleDialog import dialog
class FalconListBase(object):
	"""全てのリストに共通する基本クラス。"""
	def __init__(self):
		pass

	def __del__(self):
		pass

class FileList(FalconListBase):
	"""ファイルとフォルダの一覧を扱うリスト。"""
	def Initialize(self,dir):
		"""ディレクトリからファイル情報を取得し、リストを初期化する。入力は絶対パスでなければならない。情報が取得できなかった場合、Falseが帰る。取得できたら、Trueが帰る。"""
		dir=dir.rstrip("\\")
		dir_spl=dir.split("\\")
		level=len(dir_spl)
		globalVars.app.say("%s%d %s" % (dir[0],level,dir_spl[level-1]))
		self.log=logging.getLogger("falcon.fileList")
		self.rootDirectory=dir
		self.log.debug("Getting file list for %s..." % self.rootDirectory)
		t=misc.Timer()
		try:
			lst=win32api.FindFiles(dir+"\\*")
		except pywintypes.error as err:
			self.log.error("Cannot open the directory! {0}".format(err))
			dialog(_("エラー"), _("フォルダを開くことができませんでした(%(error)s)") % {"error": str(err)})
			return False
		#end except
		self.files=[]
		self.folders=[]
		del lst[0:1]
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
		return True
	def GetColumns(self):
		"""このリストのカラム情報を返す。"""
		return [_("ファイル名"),_("サイズ"),_("更新"),_("属性"),_("種類")]

	def GetItems(self):
		"""リストの中身を文字列タプルで取得する。フォルダが上にくる。"""
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
		globalVars.app.say(_("ドライブ洗濯"))
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

	def GetColumns(self):
		"""このリストのカラム情報を返す。"""
		return [_("名称"),_("空き"),_("合計"),_("種類")]

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
		"""リストの中身を取得する。"""
		lst=[]
		for elem in self.drives:
			lst.append(elem.GetListTuple())
		return lst

	def GetElement(self,index):
		"""インデックスを指定して、対応するリスト内のオブジェクトを返す。"""
		return self.drives[index]

class StreamList(FalconListBase):
	"""NTFS 副ストリームを扱うリスト。"""
	def Initialize(self,file):
		"""ファイル名から副ストリーム情報を取得し、リストを初期化する。入力は絶対パスでなければならない。情報が取得できなかった場合、Falseが帰る。取得できたら、Trueが帰る。"""
		file_spl=file.split("\\")
		self.rootDirectory=file
		level=len(file_spl)
		globalVars.app.say("%s%d %s" % (file[0],level,file_spl[level-1]))
		self.log=logging.getLogger("falcon.streamList")
		self.log.debug("Getting stream list for %s..." % file)
		t=misc.Timer()
		try:
			lst=win32file.FindStreams(file)
		except win32file.error as er:
			dialog(_("エラー"), _("NTFS 副ストリーム情報を取得できませんでした(%(error)s)") % {"error": str(er)})
			return False
		#end 情報取得失敗
		self.streams=[]
		for elem in lst:
			fullpath=file+":"+elem[1]
			s=browsableObjects.Stream()
			s.Initialize(file,elem[1],fullpath,elem[0])
			self.streams.append(s)
		#end 追加ループ
		self.log.debug("stream list created in %d milliseconds." % t.elapsed)
		return True

	def GetColumns(self):
		"""このリストのカラム情報を返す。"""
		return [_("ストリーム名"),_("サイズ")]

	def GetItems(self):
		"""リストの中身を文字列タプルで取得する。"""
		lst=[]
		for elem in self.streams:
			lst.append(elem.GetListTuple())
		return lst

	def GetElement(self,index):
		"""インデックスを指定して、対応するリスト内のオブジェクトを返す。"""
		return self.streams[index]
