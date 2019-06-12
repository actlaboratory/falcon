# -*- coding: utf-8 -*-
#Falcon browsable objects
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import os
import misc
import win32file

class FalconBrowsableBase(object):
	"""全ての閲覧可能オブジェクトに共通する基本クラス。"""
	def __init__(self):
		pass

	def __del__(self):
		pass

class File(FalconBrowsableBase):
	"""ファイルを表す。このオブジェクトは情報を保持するだけで、指し示すファイルにアクセスすることはない。フルパスは計算可能なのだが、二重に値を生成したくはないので、あえて値を渡すようにしている。"""
	def Initialize(self,directory="", basename="", fullpath="", size=-1, modDate=None, attributes=-1, typeString=""):
		"""必要な情報をセットする"""
		self.directory=directory
		self.basename=basename
		self.fullpath=directory+"\\"+basename
		self.size=size
		self.modDate=modDate
		self.attributes=attributes
		self.typeString=typeString

	def GetListTuple(self):
		"""表示に必要なタプルを返す。"""
		return (self.basename, self.size, misc.PTime2string(self.modDate), self.attributes, self.typeString)

class Folder(File):
	def GetListTuple(self):
		"""表示に必要なタプルを返す。フォルダなのでサイズは <dir> にする。"""
		return (self.basename, "<dir>", misc.PTime2string(self.modDate), self.attributes, self.typeString)

class Drive(FalconBrowsableBase):
	"""ドライブを表す。"""
	def Initialize(self, letter, free, total, type, name=""):
		"""必要な情報をセットする"""
		self.letter=letter
		self.free=free
		self.total=total
		self.type=type
		self.UpdateTypeString()
		self.name=name

	def UpdateTypeString(self):
		"""タイプの数値を文字列に変換し、self.typeString にセットする。"""
		if self.type==win32file.DRIVE_CDROM:
			self.typeString=_("CD-ROMドライブ")
		elif self.type==win32file.DRIVE_FIXED:
			self.typeString=_("ローカル ディスク")
		elif self.type==win32file.DRIVE_NO_ROOT_DIR:
			self.typeString=_("ルートディレクトリなし")
		elif self.type==win32file.DRIVE_RAMDISK:
			self.typeString=_("RAM ディスク")
		elif self.type==win32file.DRIVE_REMOVABLE:
			self.typeString=_("リムーバブル ディスク")
		elif self.type==win32file.DRIVE_UNKNOWN:
			self.typeString=_("不明")

	def GetListTuple(self):
		"""表示に必要なタプルを返す。"""
		return (self.name+"("+self.letter+")", misc.ConvertBytesTo(self.free, misc.UNIT_AUTO, True), misc.ConvertBytesTo(self.total, misc.UNIT_AUTO, True), self.typeString)

class Stream(FalconBrowsableBase):
	"""NTFS 副ストリームを表す。このオブジェクトは情報を保持するだけで、指し示すファイルにアクセスすることはない。フルパスは計算可能なのだが、二重に値を生成したくはないので、あえて値を渡すようにしている。"""
	def Initialize(self,file="", basename="", fullpath="", size=-1):
		"""必要な情報をセットする"""
		self.file=file
		self.basename=basename
		self.fullpath=fullpath
		self.size=size

	def GetListTuple(self):
		"""表示に必要なタプルを返す。"""
		return (self.basename, self.size)
