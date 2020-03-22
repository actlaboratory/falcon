# -*- coding: utf-8 -*-
#Falcon miscellaneous helper objects
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import ctypes
import os
import time
import hashlib
import winreg
import win32api
import win32file
import globalVars
from logging import getLogger
from simpleDialog import dialog


log=getLogger("falcon.misc")

falconHelper=ctypes.cdll.LoadLibrary("falconHelper.dll")

class Timer:
	"""シンプルなタイマー。経過時間や処理時間を計測するのに使う。単位は秒で、float。"""
	def __init__(self):
		self.started=time.time()

	@property
	def elapsed(self):
		return time.time()-self.started

#ヘルパー関数群

UNIT_AUTO=-1
UNIT_B=0
UNIT_KB=1
UNIT_MB=2
UNIT_GB=3
UNIT_TB=4
UNIT_STR=("Bytes", "KB", "MB", "GB", "TB")

def ConvertBytesTo(b, unit, appendUnit=False):
	"""バイト数を受け取って、指定された単位を使ったサイズを返す。appendUnit=True にすると、単位の文字列を最後に付けてくれる。"""
	if b<0:return ""
	num=0
	if unit==UNIT_AUTO: unit=DetermineSizeUnit(b)
	if unit==UNIT_B:
		num=b
	elif unit==UNIT_KB:
		num=b/1024
	elif unit==UNIT_MB:
		num=b/1024/1024
	elif unit==UNIT_GB:
		num=b/1024/1024/1024
	if unit==UNIT_TB:
		num=b/1024/1024/1024/1024
	#end 単位
	if not unit==UNIT_B:
		ret="%.2f" % num
	else:
		ret=""+str(num)
	if appendUnit: ret+=UNIT_STR[unit]
	return ret

def DetermineSizeUnit(b):
	"""バイト数を受け取って、それをサイズ単位に変換する際に最適な単位を、UNIT_* 定数で返す。"""
	global UNIT_B, UNIT_KB, UNIT_MB, UNIT_GB
	m=1024;
	if b<m: return UNIT_B
	m*=1024
	if b<m: return UNIT_KB
	m*=1024
	if b<m: return UNIT_MB
	m*=1024;
	if b<m: return UNIT_GB;
	return UNIT_TB;

def PTime2string(ptime):
	"""ptime 形式のオブジェクトを受け取って、人間が読めるタイムスタンプ文字列に変換して返す。"""
	return "%04d/%02d/%02d %02d:%02d:%02d" % (ptime.year, ptime.month, ptime.day, ptime.hour, ptime.minute, ptime.second)

#ptimeをwx.DateTimeに変換する
def PTimeToDateTime(pTime):
	return wx.DateTime(pTime.day,pTime.month,pTime.year,pTime.hour,pTime.minute,pTime.second,pTime.msec)

def attrib2dward(readonly=False, hidden=False, system=False, archive=False):
	ret=0
	if readonly is True: ret=ret|win32file.FILE_ATTRIBUTE_READONLY
	if hidden is True: ret=ret|win32file.FILE_ATTRIBUTE_HIDDEN
	if system is True: ret=ret|win32file.FILE_ATTRIBUTE_SYSTEM
	if archive is True: ret=ret|win32file.FILE_ATTRIBUTE_ARCHIVE
	if ret==0: ret=win32file.FILE_ATTRIBUTE_NORMAL
	return ret

def getDiscDriveTypes():
	ptr=falconHelper.getDiscDriveTypes()
	s=ctypes.c_char_p(ptr).value
	falconHelper.releasePtr(ptr)
	s2=s.decode('utf-8').split("\n")
	ret={}
	for elem in s2:
		if elem=="": continue
		tmp=elem.split(",")
		ret[tmp[0].rstrip(":\\")]=(tmp[1],tmp[2])
	#end for
	return ret
#end getDiscDriveTypes

def GetContextMenu(path):
	path_bytes=path.encode('UTF-16LE')
	ptr=falconHelper.getContextMenu(path_bytes)
	s=ctypes.c_char_p(ptr).value
	falconHelper.releasePtr(ptr)
	s2=s.decode('UTF-8')
	return s2

def DestroyContextMenu():
	falconHelper.destroyContextMenu()

def ExecContextMenuAction(id):
	falconHelper.execContextMenuAction(id)

def disableWindowStyleFlag(hwnd,flag):
	"""指定されたウィンドウハンドルの DWL_STYLE の値を撮って、指定されたフラグを折る。"""
	value=win32api.GetWindowLong(hwnd,-16)#-16 が DWL_STYLE らしい
	tmp=0xffffffff-flag
	value=value&tmp
	win32api.SetWindowLong(hwnd,-16,value)

def IteratePaths(path,append_eol=False):
	"""FindFirstFile 系を使って、パス名をイテレートする。append_eol=True にすると、最後に "eol" という1行をリストに入れるので、検索の終了判定などに使える。"""
	for elem in win32file.FindFilesIterator(path+"\\*"):
		if elem[8]=="." or elem[8]=="..": continue
		if elem[0]&win32file.FILE_ATTRIBUTE_DIRECTORY: 
			yield from IteratePaths(os.path.join(path,elem[8]))
		#end ディレクトリ
		yield os.path.join(path,elem[8])
	#EOL挿入
	if append_eol: yield "eol"

def GetDirectorySize(path):
	"""ディレクトリのサイズをバイト数で返す。"""
	total = 0
	try:
		with os.scandir(path) as it:
			for entry in it:
				if entry.is_file():
					total += entry.stat().st_size
				elif entry.is_dir():
					s=GetDirectorySize(entry.path)
					if s==-1: return -1
					total+=s

	except OSError as er:
		log.error("GetDirectorySize failed (%s" % er)
		return -1
	#end except
	return total

def GetExecutableState(path):
	"""指定されたファイルパスが、実行可能ファイルであろうかどうかを調べて boolean で返す。"""
	return os.path.splitext(path)[1].upper() in os.environ["pathext"].split(";")

def calcHash(path,algo):
	h = hashlib.new(algo)
	len = hashlib.new(algo).block_size * 0x800
	with open(path,'rb') as f:
		BinaryData = f.read(len)
		while BinaryData:
			h.update(BinaryData)
			BinaryData = f.read(len)
			return h.hexdigest()

#環境変数PATHに値を追加
def addPath(paths):
	try:
		h=winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,"Environment",access=winreg.KEY_WRITE | winreg.KEY_READ)
		for path in paths:
			winreg.SetValueEx(h, 'Path', 0, winreg.REG_SZ,winreg.QueryValueEx(h, 'Path')[0]+";"+path)
		winreg.CloseKey(h)
		return True
	except:
		return False

def RunFile(path, admin=False,prm=""):
	"""ファイルを起動する。admin=True の場合、管理者として実行する。"""
	path=os.path.expandvars(path)
	msg="running %s as admin" % (path) if admin else "running %s" % (path)
	log.debug(msg)
	msg=_("管理者で起動") if admin else _("起動")
	globalVars.app.say(msg)
	error=""
	if admin:
		try:
			executable=GetExecutableState(path)
			p=path if executable else "cmd"
			a=prm if executable else "/c "+path+" "+prm
			ret=shell.ShellExecuteEx(shellcon.SEE_MASK_NOCLOSEPROCESS,0,"runas",p,a)
		except pywintypes.error as e:
			error=str(e)
		#end shellExecuteEx failure
	else:
		try:
			win32api.ShellExecute(0,"open",path,prm,"",1)
		except win32api.error as er:
			error=str(er)
		#end shellExecute failure
	#end admin or not
	if error!="":
		dialog(_("エラー"),_("ファイルを開くことができませんでした(%(error)s)") % {"error": error})
	#end ファイル開けなかった
#end RunFile
