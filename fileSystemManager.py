# -*- coding: utf-8 -*-
#Falcon file system objects
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import win32api
import re

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

def ValidationObjectName(s):
	"""ファイルやディレクトリの名前sに何らかの問題があればその内容を返す"""

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


class FileSystemBase(object):
	def __init__(self):
		self.canMakeHardLink=True
		self.canMakeSymbolicLink=True

class NTFS(FileSystemBase):
	def __str__(self):
		return "NTMS"

class FAT32(FileSystemBase):
	def __str__(self):
		return "FAT32"
