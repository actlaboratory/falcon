# -*- coding: utf-8 -*-
#Falcon file system objects
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import win32api

def GetFileSystemObject(letter):
	"""
	ドライブレターから、そのドライブのファイルシステムを取得する。

	:param letter: ドライブレター1文字。
	:type letter: str
	:rtype: str
	"""
	name=win32api.GetVolumeInformation("%s:\\" % (letter))[4]
	try:
		cls=globals()[name]
	except KeyError:
		return None
	#end keyError
	return cls()

class FileSystemBase(object):
	def __init__(self):
		self.canMakeHardLink=True
		self.canMakeSymbolicLink=True

class NTFS(FileSystemBase):
	pass
