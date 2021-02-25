# -*- coding: utf-8 -*-
#Falcon browsable objects
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese.

import os
import win32con
import win32file
import logging

import constants
import misc
import globalVars

class FalconBrowsableBase():
	"""全ての閲覧可能オブジェクトに共通する基本クラス。"""
	__slots__=["attributes","attributesString","log","longAttributesString","canLnkTarget","canHardLinkTarget","canSynLinkTarget","list_backgroundColour"]

	def __init__(self):
		self.log=logging.getLogger("falcon.browsableObjects")
		self.canLnkTarget=True
		self.canHardLinkTarget=True
		self.canSynLinkTarget=True
		self.list_backgroundColour=None

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

		if attrib&win32con.FILE_ATTRIBUTE_REPARSE_POINT:
			if not self.longAttributesString=="":
				self.longAttributesString+="・"
			self.longAttributesString+= _("リパースポイント")

		if self.longAttributesString=="":
			self.longAttributesString="なし"
		return

	def IsReparsePoint(self):
		return self.attributes&win32con.FILE_ATTRIBUTE_REPARSE_POINT>0

	def __str__(self):
		return "<"+self.__class__.__name__+" "+self.basename+">"

	def __repr__(self):
		return "<"+self.__class__.__name__+" "+self.basename+">"

	def GetListTuple(self):
		raise NotImplementedError

	def __getitem__(self,index):
		return self.GetListTuple()[index]

	def __len__(self):
		return len(self.GetListTuple())

	def __setitem__(self,index,obj):
		raise NotImplementedError


class File(FalconBrowsableBase):
	"""ファイルを表す。このオブジェクトは情報を保持するだけで、指し示すファイルにアクセスすることはない。フルパスは計算可能なのだが、二重に値を生成したくはないので、あえて値を渡すようにしている。"""
	__slots__=["basename","creationDate","directory","fullpath","modDate","shortName","size","typeString","hIcon"]

	def Initialize(self,directory="", basename="", fullpath="", size=-1, modDate=None, attributes=-1, typeString="",creationDate=None,shortName="",hIcon=-1):
		"""必要な情報をセットする。継承しているクラスのうち、grepItemだけはここを通らないので注意。"""
		self.directory=directory
		self.basename=basename
		self.fullpath=os.path.join(directory,basename)
		self.size=size
		self.modDate=modDate.astimezone(globalVars.app.timezone)
		self.creationDate=creationDate.astimezone(globalVars.app.timezone)
		self.attributes=attributes
		self.GetAttributesString()
		self.typeString=typeString
		self.shortName=shortName
		self.hIcon=hIcon

		if self.fullpath[0:2]=="\\\\":
			self.canHardLinkTarget=False

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

	def GetRootDrivePath(self):
		return misc.GetRootObject(self.fullpath).fullpath

class Folder(File):
	__slots__=["fileCount","dirCount"]

	def __init__(self,**args):
		super().__init__(*args)
		self.canHardLinkTarget=False
		self.fileCount=-1
		self.dirCount=-1

	def GetListTuple(self):
		"""表示に必要なタプルを返す。フォルダなのでサイズ不明(-1)の場合があり、この場合は <dir> にする。"""
		if self.size<0:
			return (self.basename, "<dir>", misc.PTime2string(self.modDate), self.attributesString, self.typeString)
		else:
			return (self.basename, misc.ConvertBytesTo(self.size,misc.UNIT_AUTO,True), misc.PTime2string(self.modDate), self.attributesString, self.typeString)

class SearchedFile(File):
	__slots__=[]

	def GetListTuple(self):
		"""表示に必要なタプルを返す。"""
		return (self.basename, misc.ConvertBytesTo(self.size,misc.UNIT_AUTO,True), self.fullpath, misc.PTime2string(self.modDate), self.attributesString, self.typeString)

class SearchedFolder(Folder):
	__slots__=[]

	def GetListTuple(self):
		"""表示に必要なタプルを返す。フォルダなのでサイズ不明(-1)の場合があり、この場合は <dir> にする。"""
		if self.size<0:
			return (self.basename, "<dir>", self.fullpath, misc.PTime2string(self.modDate), self.attributesString, self.typeString)
		else:
			return (self.basename, misc.ConvertBytesTo(self.size,misc.UNIT_AUTO,True), self.fullpath, misc.PTime2string(self.modDate), self.attributesString, self.typeString)

class GrepItem(File):
	def Initialize(self,ln,preview,fileobject):
		"""grepの結果は、ファイルの情報に加えて、行数・プレビュー・ヒット数を含む。ヒット数は、後から設定する。ファイル名などは、与えられたファイルオブジェクトからとる。"""
		self.directory=fileobject.directory
		self.basename=fileobject.basename
		self.fullpath=fileobject.fullpath
		self.size=fileobject.size
		self.modDate=fileobject.modDate
		self.creationDate=fileobject.creationDate
		self.attributes=fileobject.attributes
		self.attributesString=fileobject.attributesString
		self.longAttributesString=fileobject.longAttributesString
		self.shortName=fileobject.shortName
		self.typeString=fileobject.typeString
		self.ln=ln
		self.preview=preview
		self.hits=0#とりあえず入れておく
		self.hIcon=fileobject.hIcon

		if self.fullpath[0:2]=="\\\\":
			self.canHardLinkTarget=False

	def SetHitCount(self,h):
		"""ヒット数を設定する。"""
		self.hits=h

	def GetListTuple(self):
		"""表示に必要なタプルを返す。"""
		return (self.basename, self.ln, self.preview, self.hits, misc.ConvertBytesTo(self.size,misc.UNIT_AUTO,True), misc.PTime2string(self.modDate), self.attributesString, self.typeString)

class Drive(FalconBrowsableBase):
	"""ドライブを表す。"""
	def Initialize(self, letter, free, total, type, name="",hIcon=-1):
		"""
			必要な情報をセットする
			変数名はNetworkResourceと互換しているため、変更した場合は両方に反映すること！

		"""
		self.letter=letter
		self.basename=letter
		self.free=free
		self.total=total
		self.type=type
		self.UpdateTypeString()
		self.basename=name
		self.fullpath=letter+":\\"
		self.hIcon=hIcon

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

	def GetRootDrivePath(self):
		return self.fullpath

class Stream(FalconBrowsableBase):
	"""NTFS 副ストリームを表す。このオブジェクトは情報を保持するだけで、指し示すファイルにアクセスすることはない。フルパスは計算可能なのだが、二重に値を生成したくはないので、あえて値を渡すようにしている。"""
	def Initialize(self,file="", basename="", fullpath="", size=-1):
		"""必要な情報をセットする"""
		self.file=file
		self.basename=basename
		self.fullpath=fullpath
		self.size=size
		self.hIcon=-1			#ストリームにアイコンはない

	def GetListTuple(self):
		"""表示に必要なタプルを返す。"""
		return (self.basename, misc.ConvertBytesTo(self.size,misc.UNIT_AUTO,True))

	def GetRootDrivePath(self):
		return misc.GetRootObject(self.fullpath).fullpath

class NetworkResource(FalconBrowsableBase):
	"""ネットワーク上のディスクリソースを表す。このオブジェクトは情報を保持するだけで、指し示すリソースにアクセスすることはない。フルパスは計算可能なのだが、二重に値を生成したくはないので、あえて値を渡すようにしている。"""

	def __init__(self):
		super().__init__()
		self.canHardLinkTarget=False

	def Initialize(self,basename="", fullpath="", address="",hIcon=-1):
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
		self.hIcon=hIcon

	def GetListTuple(self):
		"""
			表示に必要なタプルを返す。
			ここもDriveと同じ内容に統一
		"""
		return (self.basename, self.letter,"", "", self.typeString)

	def GetRootDrivePath(self):
		return self.basename

class PastProgressItem(FalconBrowsableBase):
	"""貼り付けにおいて、渓谷/エラーになったファイルを表す。"""
	def __init__(self):
		super().__init__()
		self.canLnkTarget=False
		self.canHardLinkTarget=False
		self.canSynLinkTarget=False

	def Initialize(self,basename="",fullpath="",status="",details=""):
		self.basename=basename
		self.fullpath=fullpath
		self.status=status
		self.details=details
		self.hIcon=0

	def GetListTuple(self):
		"""表示に必要なタプルを返す。"""
		return (self.fullpath, self.status, self.details)

	def __str__(self):
		return "<past progress item>"

	def __repr__(self):
		return "<past progress item>"

class PastProgressHeader(PastProgressItem):
	def __init__(self):
		PastProgressItem.__init__(self)
		self.percentage=0

	def Initialize(self,basename="",fullpath="",status="",details="", percentage=0):
		PastProgressItem.Initialize(self,basename,fullpath,status,details)
		self.percentage=percentage

	def SetPercentage(self,percentage):
		self.percentage=percentage

	def GetListTuple(self):
		"""表示に必要なタプルを返す。"""
		return (self.fullpath, self.status, "%s(%s%%)" % (self.details,self.percentage))
