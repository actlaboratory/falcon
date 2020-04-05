# -*- coding: utf-8 -*-
#Falcon browsable objects
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese.

import os
import win32file
import logging
import constants
import misc
import globalVars

class FalconBrowsableBase():
	"""全ての閲覧可能オブジェクトに共通する基本クラス。"""
	__slots__=["attributes","attributesString","log","longAttributesString"]

	def __init__(self):
		self.log=logging.getLogger("falcon.browsableObjects")
	def GetAttributesString(self):
		"""属性の文字列を設定する。"""
		attrib=self.attributes
		self.attributesString=""
		self.longAttributesString=""

		if attrib&win32file.FILE_ATTRIBUTE_READONLY:
			self.attributesString+= "R"
			self.longAttributesString+= _("読取専用")
		else:
			self.attributesString+="-"

		if attrib&win32file.FILE_ATTRIBUTE_HIDDEN:
			self.attributesString+="H"
			if not self.longAttributesString=="":
				self.longAttributesString+="・"
			self.longAttributesString+= _("隠し")
		else:
			self.attributesString+="-"

		if attrib&win32file.FILE_ATTRIBUTE_SYSTEM:
			self.attributesString+="S"
			if not self.longAttributesString=="":
				self.longAttributesString+="・"
			self.longAttributesString+= _("システム")
		else:
			self.attributesString+="-"

		if self.longAttributesString=="":
			self.longAttributesString="なし"
		return

class File(FalconBrowsableBase):
	"""ファイルを表す。このオブジェクトは情報を保持するだけで、指し示すファイルにアクセスすることはない。フルパスは計算可能なのだが、二重に値を生成したくはないので、あえて値を渡すようにしている。"""
	__slots__=["basename","creationDate","directory","fullpath","modDate","shortName","size","typeString"]

	def Initialize(self,directory="", basename="", fullpath="", size=-1, modDate=None, attributes=-1, typeString="",creationDate=None,shortName=""):
		"""必要な情報をセットする"""
		self.directory=directory
		self.basename=basename
		self.fullpath=directory+"\\"+basename
		self.size=size
		self.modDate=modDate.astimezone(globalVars.app.timezone)
		self.creationDate=creationDate.astimezone(globalVars.app.timezone)
		self.attributes=attributes
		self.GetAttributesString()
		self.typeString=typeString
		self.shortName=shortName

	def GetListTuple(self):
		"""表示に必要なタプルを返す。"""
		return (self.basename, misc.ConvertBytesTo(self.size,misc.UNIT_AUTO,True), misc.PTime2string(self.modDate), self.attributesString, self.typeString)

	def GetNewAttributes(self,checks):
		"""属性変更の時に使う。チェック状態のリストを受け取って、新しい属性値を帰す。変更の必要がなければ、-1を帰す。"""
		attrib=self.attributes
		#繰り返しで回せるように、先にフラグ達をリストに入れておく
		flags=[win32file.FILE_ATTRIBUTE_READONLY,win32file.FILE_ATTRIBUTE_HIDDEN,win32file.FILE_ATTRIBUTE_SYSTEM,win32file.FILE_ATTRIBUTE_ARCHIVE]
		for i in range(len(flags)):
			if checks[i]==constants.NOT_CHECKED:#チェックされてないのでフラグを折る
				if attrib&flags[i]: attrib-=flags[i]
			elif checks[i]==constants.FULL_CHECKED:#チェック状態なのでフラグを立てる
				if not attrib&flags[i]: attrib+=flags[i]
			#end フラグを立てるか折るか
		#end フラグの数だけ
		return attrib if self.attributes!=attrib else -1
	#end GetNewAttributes

class Folder(File):
	__slots__=[]

	def GetListTuple(self):
		"""表示に必要なタプルを返す。フォルダなのでサイズ不明(-1)の場合があり、この場合は <dir> にする。"""
		if self.size<0:
			return (self.basename, "<dir>", misc.PTime2string(self.modDate), self.attributesString, self.typeString)
		else:
			return (self.basename, misc.ConvertBytesTo(self.size,misc.UNIT_AUTO,True), misc.PTime2string(self.modDate), self.attributesString, self.typeString)

	class GrepItem(FalconBrowsableBase):
		def Initialize(self,ln,preview,fileobject):
			"""grepの結果は、ファイルの情報に加えて、行数・プレビュー・ヒット数を含む。ヒット数は、後から設定する。ファイル名などは、与えられたファイルオブジェクトからとる。"""
			self.basename=fileobject.basename
			self.size=basename.size
			self.modDate=fileobject.modDate
			self.attributes=fileobject.attributes
			self.typeString=fileobject.typeString
			self.ln=ln
			self.preview=preview
			self.hits=0#とりあえず入れておく

		def SetHitCount(self,h):
			"""ヒット数を設定する。"""
			self.hits=h

	def GetListTuple(self):
		"""表示に必要なタプルを返す。"""
		return (self.basename, self.hits, self.ln, self.preview, misc.ConvertBytesTo(self.size,misc.UNIT_AUTO,True), misc.PTime2string(self.modDate), self.attributesString, self.typeString)

class Drive(FalconBrowsableBase):
	"""ドライブを表す。"""
	def Initialize(self, letter, free, total, type, name=""):
		"""
			必要な情報をセットする
			変数名はNetworkResourceと互換しているため、変更した場合は両方に反映すること！

		"""
		self.letter=letter
		self.free=free
		self.total=total
		self.type=type
		self.UpdateTypeString()
		self.basename=name
		self.fullpath=letter+":"

	def UpdateTypeString(self):
		"""タイプの数値を文字列に変換し、self.typeString にセットする。"""
		if self.type==win32file.DRIVE_CDROM:
			discDrives=misc.getDiscDriveTypes()
			self.typeString=discDrives[self.letter][1]+_(" ドライブ")
		elif self.type==win32file.DRIVE_FIXED:
			self.typeString=_("ローカル ディスク")
		elif self.type==win32file.DRIVE_NO_ROOT_DIR:
			self.typeString=_("ルートディレクトリなし")
		elif self.type==win32file.DRIVE_RAMDISK:
			self.typeString=_("RAM ディスク")
		elif self.type==win32file.DRIVE_REMOVABLE:
			self.typeString=_("リムーバブル ディスク")
		elif self.type==win32file.DRIVE_REMOTE:
			self.typeString=_("ネットワーク")
		elif self.type==win32file.DRIVE_UNKNOWN:
			self.typeString=_("不明")
		else:
			self.log.warning("Unknown drivetype found("+self.type+")")
			self.typeString=_("不明")


	def GetListTuple(self):
		"""
			表示に必要なタプルを返す。
			変更した場合はNetworkResourceの方にも反映すること！
		"""
		return (self.basename, self.letter, misc.ConvertBytesTo(self.free, misc.UNIT_AUTO, True), misc.ConvertBytesTo(self.total, misc.UNIT_AUTO, True), self.typeString)

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
		return (self.basename, misc.ConvertBytesTo(self.size,misc.UNIT_AUTO,True))

class NetworkResource(FalconBrowsableBase):
	"""ネットワーク上のディスクリソースを表す。このオブジェクトは情報を保持するだけで、指し示すリソースにアクセスすることはない。フルパスは計算可能なのだが、二重に値を生成したくはないので、あえて値を渡すようにしている。"""
	def Initialize(self,basename="", fullpath="", address=""):
		"""
			必要な情報をセットする
			ドライブリストに表示するため、変数名はDriveのものと互換
		"""
		self.basename=basename
		self.fullpath=fullpath
		self.letter=""
		self.free=-1
		self.total=-1
		self.type=-1
		self.typeString=_("ネットワークリソース")
		self.address=address

	def GetListTuple(self):
		"""
			表示に必要なタプルを返す。
			ここもDriveと同じ内容に統一
		"""
		return (self.basename, self.letter,"", "", self.typeString)
