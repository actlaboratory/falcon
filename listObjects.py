# -*- coding: utf-8 -*-
#Falcon generic list management
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import gettext
import os
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
from win32com.shell import shell, shellcon

SORT_ASCENDING=False
SORT_DESCENDING=1

SORT_TYPE_BASENAME=1
SORT_TYPE_FILESIZE=2
SORT_TYPE_MODDATE=3
SORT_TYPE_ATTRIBUTES=4
SORT_TYPE_TYPESTRING=5
SORT_TYPE_VOLUMELABEL=6
SORT_TYPE_DRIVELETTER=7
SORT_TYPE_TOTALSPACE=8
SORT_TYPE_FREESPACE=9

SORT_DESCRIPTIONS=None

READONLY=0
HIDDEN=1
SYSTEM=2
ARCHIVE=3

def GetSortDescription(attrib):
	global SORT_DESCRIPTIONS
	if SORT_DESCRIPTIONS is None:
		SORT_DESCRIPTIONS={
			SORT_TYPE_BASENAME: _("ファイル名"),
			SORT_TYPE_FILESIZE: _("ファイルサイズ"),
			SORT_TYPE_MODDATE:_("更新日時"),
			SORT_TYPE_ATTRIBUTES:_("属性"),
			SORT_TYPE_TYPESTRING:_("種類"),
			SORT_TYPE_VOLUMELABEL:_("ラベル"),
			SORT_TYPE_DRIVELETTER:_("ラベル"),
			SORT_TYPE_FREESPACE:_("空き"),
			SORT_TYPE_TOTALSPACE:_("合計")
		}
	#end 辞書作る
	return SORT_DESCRIPTIONS[attrib]

class FalconListBase(object):
	"""全てのリストに共通する基本クラス。"""
	def __init__(self):
		self.supportedSorts=[]
		self.sortCursor=0
		self.sortDescending=0

	def Search(self,search):
		"""文字列からインデックス番号に変換する。"""
		lst=self.GetItems()
		found=-1
		i=0
		for elem in lst:
			if elem[0]==search:
				found=i
				i+=1
				break
			#end 検索
		#end for
		return found

	def GetSortCursor(self):
		return self.sortCursor

	def SetSortCursor(self, val=-1):
		"""インデックスを指定すると、その位置へソートカーソルを移動。パラメータなしで、次のソートへ移動。実際にソートを適用するには、ApplySort を実行する。"""
		if val==self.sortCursor: return
		if len(self.supportedSorts)==0:
			globalVars.app.say(_("このリストはソートできません。"))
			return
		#ソート非対応
		self.sortCursor=self.sortCursor+1 if val==-1 else val
		if self.sortCursor==len(self.supportedSorts): self.sortCursor=0
		if self.sortCursor<0: self.sortCursor=0
		globalVars.app.say(GetSortDescription(self.supportedSorts[self.sortCursor]))

	def SetSortDescending(self,d):
		if d==self.sortDescending: return
		self.sortDescending=d
		s=_("昇順") if d==0 else _("降順")
		globalVars.app.say(s)

	def GetSortDescending(self):
		return self.sortDescending

	def ApplySort(self):
		"""ソートを適用。並び順と照準/降順は、setSortCursor / SetSortDescending で設定しておく。"""
		if len(self.supportedSorts)==0: return
		self._sort(self.supportedSorts[self.sortCursor],self.sortDescending)

	def GetSupportedSorts(self):
		"""サポートされているソートのタイプを取得する。"""
		return self.supportedSorts

	def _getSortFunction(self,attrib):
		if attrib==SORT_TYPE_BASENAME: return lambda x: x.basename
		if attrib==SORT_TYPE_FILESIZE: return lambda x: x.size
		if attrib==SORT_TYPE_MODDATE: return lambda x: x.modDate
		if attrib==SORT_TYPE_ATTRIBUTES: return lambda x: x.attributes
		if attrib==SORT_TYPE_TYPESTRING: return lambda x: x.typeString
		if attrib==SORT_TYPE_VOLUMELABEL: return lambda x: x.basename
		if attrib==SORT_TYPE_DRIVELETTER: return lambda x: x.letter
		if attrib==SORT_TYPE_FREESPACE: return lambda x: x.free
		if attrib==SORT_TYPE_TOTALSPACE: return lambda x: x.total


class FileList(FalconListBase):
	"""ファイルとフォルダの一覧を扱うリスト。"""
	def __init__(self):
		super().__init__()
		self.supportedSorts=[SORT_TYPE_BASENAME,SORT_TYPE_FILESIZE,SORT_TYPE_MODDATE,SORT_TYPE_ATTRIBUTES,SORT_TYPE_TYPESTRING]
		self.log=logging.getLogger("falcon.fileList")

	def Update(self):
		return self.Initialize(self.rootDirectory,self.sortCursor,self.sortDescending,True)

	def Initialize(self,dir, sorting=0,descending=0,silent=False):
		"""ディレクトリからファイル情報を取得し、リストを初期化する。入力は絶対パスでなければならない。情報が取得できなかった場合、errorCodes.OK以外が返る。silentがTrueなら読み上げは行われない。"""
		self.sortCursor=sorting
		self.sortDescending=descending
		self.files=[]
		self.folders=[]
		if isinstance(dir,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			self._copyFromList(dir)
			return errorCodes.OK
		#end copy
		dir=dir.rstrip("\\")
		dir_spl=dir.split("\\")
		level=len(dir_spl)
		if not silent:
			globalVars.app.say("%s%d %s" % (dir[0],level,dir_spl[level-1]))
		self.rootDirectory=dir
		self.log.debug("Getting file list for %s..." % self.rootDirectory)
		t=misc.Timer()
		try:
			lst=win32api.FindFiles(dir+"\\*")
		except pywintypes.error as err:
			self.log.error("Cannot open the directory! {0}".format(err))
			dialog(_("エラー"), _("フォルダを開くことができませんでした(%(error)s)") % {"error": str(err)})
			return errorCodes.FATAL
		#end except
		if len(lst)==2:
			lst=[]
			self.log.debug("Blank folder.")
			return errorCodes.OK
		#end 空のフォルダだったらさっさと帰る
		del lst[0:2]
		for elem in lst:
			fullpath=dir+"\\"+elem[8]
			ret, shfileinfo=shell.SHGetFileInfo(fullpath,0,shellcon.SHGFI_ICON|shellcon.SHGFI_TYPENAME)
			if os.path.isfile(fullpath):
				f=browsableObjects.File()
				f.Initialize(dir,elem[8],fullpath,(elem[4]<<32)+elem[5], elem[3], elem[0], shfileinfo[4],elem[1])
				self.files.append(f)
			else:
				f=browsableObjects.Folder()
				f.Initialize(dir,elem[8],fullpath,0,elem[3], elem[0], shfileinfo[4],elem[1])
				self.folders.append(f)
			#end どっちについかするか？
		#end 追加ループ
		self.log.debug("File list created in %f seconds." % t.elapsed)
		self.log.debug(str(len(self.folders))+" directories and "+str(len(self.files))+" files found.")
		if self.sortCursor!=0:
			self.log.debug("Triggering sorting")
			self.ApplySort()
		#end ソートが必要ならソート
		return errorCodes.OK

	def _copyFromList(self,lst):
		self.log.debug("Copying from file list...")
		for elem in lst:
			if isinstance(elem,browsableObjects.File):
				self.files.append(elem)
			elif isinstance(elem,browsableObjects.Folder):
				self.folders.append(elem)
			#end ファイルかフォルダか
		#end for
	#end _copyFromList

	def GetColumns(self):
		"""このリストのカラム情報を返す。"""
		return {
			_("ファイル名"):wx.LIST_FORMAT_LEFT,
			_("サイズ"):wx.LIST_FORMAT_RIGHT,
			_("更新"):wx.LIST_FORMAT_LEFT,
			_("属性"):wx.LIST_FORMAT_LEFT,
			_("種類"):wx.LIST_FORMAT_LEFT
		}

	def GetItems(self):
		"""リストの中身を文字列タプルで取得する。フォルダが上にくる。"""
		lst=[]
		for elem in self.folders:
			lst.append(elem.GetListTuple())
		for elem in self.files:
			lst.append(elem.GetListTuple())
		return lst

	def GetItemPaths(self):
		"""リストの中身をパスのリストで取得する。フォルダが上にくる。"""
		lst=[]
		for elem in self.folders:
			lst.append(elem.fullpath)
		for elem in self.files:
			lst.append(elem.fullpath)
		return lst

	def GetItemNames(self):
		"""リストの中身をファイル名のリストで取得する。フォルダが上にくる。"""
		lst=[]
		for elem in self.folders:
			lst.append(elem.basename)
		for elem in self.files:
			lst.append(elem.basename)
		return lst

	def GetElement(self,index):
		"""インデックスを指定して、対応するリスト内のオブジェクトを返す。"""
		return self.folders[index] if index<len(self.folders) else self.files[index-len(self.folders)]

	def GetTopFileIndex(self):
		"""先頭ファイルのインデックス番号を返す。"""
		return len(self.folders)

	def _sort(self,attrib, descending):
		"""指定した要素で、リストを並べ替える。"""
		self.log.debug("Begin sorting (attrib %s, descending %s)" % (attrib, descending))
		t=misc.Timer()
		f=self._getSortFunction(attrib)
		self.files.sort(key=f, reverse=(descending==1))
		self.folders.sort(key=f, reverse=(descending==1))
		self.log.debug("Finished sorting (%f seconds)" % t.elapsed)

	def GetAttributeCheckState(self):
		"""このリストに入っているファイルを1個ずつとって、対応するファイルの属性値を取得していく。各属性に対して、リスト内の全てのファイルが持っていれば ATTRIB_FULL_CHECKED を帰す。一部のファイルが持っていれば、 ATTRIB_HALF_CHECKED を帰す。どのファイルも持っていなければ、 ATTRIB_NOT_CHECKED を帰す。このデータを、リストにして帰す。"""
		found=[0,0,0,0]#各属性を見つけた個数
		ret=[constants.NOT_CHECKED, constants.NOT_CHECKED, constants.NOT_CHECKED, constants.NOT_CHECKED]#帰す値
		for elem in self:
			attrib=elem.attributes
			if attrib&win32file.FILE_ATTRIBUTE_READONLY:
				found[READONLY]+=1
				ret[READONLY]=constants.HALF_CHECKED
			#end readonly
			if attrib&win32file.FILE_ATTRIBUTE_HIDDEN:
				found[HIDDEN]+=1
				ret[HIDDEN]=constants.HALF_CHECKED
			#end hidden
			if attrib&win32file.FILE_ATTRIBUTE_SYSTEM:
				found[SYSTEM]+=1
				ret[SYSTEM]=constants.HALF_CHECKED
			#end system
			if attrib&win32file.FILE_ATTRIBUTE_ARCHIVE:
				found[ARCHIVE]+=1
				ret[ARCHIVE]=constants.HALF_CHECKED
			#end system
		#end for
		l=len(self)
		if found[READONLY]==l: ret[READONLY]=constants.FULL_CHECKED
		if found[HIDDEN]==l: ret[HIDDEN]=constants.FULL_CHECKED
		if found[SYSTEM]==l: ret[SYSTEM]=constants.FULL_CHECKED
		if found[ARCHIVE]==l: ret[ARCHIVE]=constants.FULL_CHECKED
		return ret

	def __iter__(self):
		lst=self.folders+self.files
		return lst.__iter__()

	def __len__(self):
		return len(self.folders)+len(self.files)

class DriveList(FalconListBase):
	"""ドライブの一覧を扱うクラス。"""
	def __init__(self):
		self.supportedSorts=[SORT_TYPE_BASENAME,SORT_TYPE_DRIVELETTER,SORT_TYPE_FREESPACE,SORT_TYPE_TOTALSPACE, SORT_TYPE_TYPESTRING]
		self.log=logging.getLogger("falcon.driveList")

	def Update(self):
		return self.Initialize(None,self.sortCursor,self.sortDescending,True)

	def Initialize(self,lst,sorting=0,descending=0,silent=False):
		"""ドライブ情報を取得し、リストを初期化する。"""
		self.sortCursor=sorting
		self.sortDescending=descending
		self.log.debug("Getting drives list...")
		self.rootDirectory=""
		t=misc.Timer()
		self.drives=[]
		self.unusableDrives=[]
		if isinstance(lst,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			self.drives=lst
			return
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
			print(elem.fullpath)
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

class StreamList(FalconListBase):
	"""NTFS 副ストリームを扱うリスト。"""
	def __init__(self):
		self.log=logging.getLogger("falcon.streamList")

	def Update(self):
		return self.Initialize(self.rootDirectory,True)

	def Initialize(self,file,silent=False):
		"""ファイル名から副ストリーム情報を取得し、リストを初期化する。入力は絶対パスでなければならない。情報が取得できなかった場合、errorCodes.OK以外が返る。。"""
		t=misc.Timer()
		self.streams=[]

		if isinstance(file,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			self.streams=file
			return
		#end copy

		file_spl=file.split("\\")
		self.rootDirectory=file
		level=len(file_spl)
		if not silent:
			globalVars.app.say("%s%d %s" % (file[0],level,file_spl[level-1]))
		self.log.debug("Getting stream list for %s..." % file)
		try:
			lst=win32file.FindStreams(file)
		except win32file.error as er:
			dialog(_("エラー"), _("NTFS 副ストリーム情報を取得できませんでした(%(error)s)") % {"error": str(er)})
			return False
		#end 情報取得失敗
		for elem in lst:
			fullpath=file+elem[1]
			s=browsableObjects.Stream()
			s.Initialize(file,elem[1],fullpath,elem[0])
			self.streams.append(s)
		#end 追加ループ
		self.log.debug("stream list created in %d milliseconds." % t.elapsed)
		self.log.debug(str(len(self.streams))+" objects found.")
		return True

	def GetColumns(self):
		"""このリストのカラム情報を返す。"""
		return {_("ストリーム名"):wx.LIST_FORMAT_LEFT,_("サイズ"):wx.LIST_FORMAT_RIGHT}

	def GetItems(self):
		"""リストの中身を文字列タプルで取得する。"""
		lst=[]
		for elem in self.streams:
			lst.append(elem.GetListTuple())
		return lst

	def GetItemPaths(self):
		"""リストの中身をフルパスのリストで取得する。"""
		lst=[]
		for elem in self.streams:
			lst.append(elem.fullpath)
		return lst

	def GetElement(self,index):
		"""インデックスを指定して、対応するリスト内のオブジェクトを返す。"""
		return self.streams[index]

	def GetItemPaths(self):
		"""リストの中身をパスのリストで取得する。フォルダが上にくる。"""
		lst=[]
		for elem in self.streams:
			lst.append(elem.fullpath)
		return lst

	def GetItemNames(self):
		"""リストの中身をファイル名のリストで取得する。フォルダが上にくる。"""
		lst=[]
		for elem in self.streams:
			lst.append(elem.basename)
		return lst
