# -*- coding: utf-8 -*-
#Falcon browsable objects
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import os
import misc

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
