# -*- coding: utf-8 -*-
#Falcon file system objects
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import win32api
import re
import os
from enum import Enum

def GetFileSystemObject(letter):
	"""
	ドライブレターから、そのドライブのファイルシステムを取得する。

	:param letter: ドライブレター1文字。
	:type letter: str
	:rtype: FileSystemBase
	"""
	name=win32api.GetVolumeInformation("%s:\\" % (letter))[4]
	try:
		cls=globals()[name]
	except KeyError:
		return None
	#end keyError
	return cls()

def ValidationObjectName(path):
	"""
		ファイルやディレクトリの名前pathに何らかの問題があればその内容を返す
		sはフルパス
	"""
	s=os.path.split(path)[1]

	#使用できない文字の確認
	ngString=[]
	for c in ("\\","/",":","*","?","\"","<",">","|"):
		if c in s:
			ngString.append(c)
	if ngString:
		tmp=""
		for c in ngString:
			if tmp!="":
				tmp+=" ・ "
			tmp+="「"+c+"」"
		tmp+=_("は、ファイルやディレクトリの名前として使用できない記号です。")
		return tmp

	#使用できない特別な名前
	for i in ("CON","AUX","PRN","NUL"):
		if re.sub("^("+i+"$)|("+i+"\\..*)",r"",s.upper())=="":
			return _("この文字列は、Windowsによって予約された特別な名前のため、ファイルやディレクトリの名前として使用できません。")
	for i in ("COM","LPT"):
		if re.sub("^("+i+"[1-9]$)|("+i+"[1-9]\\..*)",r"",s.upper())=="":
			return _("この文字列は、Windowsによって予約された特別な名前のため、ファイルやディレクトリの名前として使用できません。")

	#末尾が.と半角スペースでないことの確認
	if re.sub("(.*\\.$)|(.* $)",r"",s.upper())=="":
		return _("名前の最後を半角の.またはスペースとすることはできません。")

	#問題なし
	return ""


class limitTypes(Enum):
	CHAR=0
	BYTE=1


class FileSystemBase(object):
	def __init__(self):
		self.canMakeHardLink=True
		self.canMakeSymbolicLink=True

	MAX_FULLPATH_LENGTH=256


class NTFS(FileSystemBase):
	def __str__(self):
		return "NTFS"

	MAX_VOLUME_LABEL_TYPE=limitTypes.CHAR
	MAX_VOLUME_LABEL_LENGTH=32
	MAX_PATH_LENGTH=255

class FAT(FileSystemBase):
	def __str__(self):
		return "FAT"

	MAX_VOLUME_LABEL_TYPE=limitTypes.BYTE
	MAX_VOLUME_LABEL_LENGTH=11
	MAX_PATH_LENGTH=12

class FAT32(FileSystemBase):
	def __str__(self):
		return "FAT32"

	MAX_VOLUME_LABEL_TYPE=limitTypes.BYTE
	MAX_VOLUME_LABEL_LENGTH=11
	MAX_PATH_LENGTH=255

class exFAT(FileSystemBase):
	def __str__(self):
		return "exFAT"

	MAX_VOLUME_LABEL_TYPE=limitTypes.BYTE
	MAX_VOLUME_LABEL_LENGTH=11
	MAX_PATH_LENGTH=255

class UDF(FileSystemBase):
	def __str__(self):
		return "UDF"

	MAX_VOLUME_LABEL_TYPE=limitTypes.CHAR
	MAX_VOLUME_LABEL_LENGTH=32
	MAX_PATH_LENGTH=255

class CDFS(FileSystemBase):
	def __str__(self):
		return "CDFS"

