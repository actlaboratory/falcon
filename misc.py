# -*- coding: utf-8 -*-
#Falcon miscellaneous helper objects
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import ctypes
import json
import socket
import pywintypes
import os
import re
import time
import hashlib
import winreg
import win32api
import win32con
import win32file

import constants
import globalVars
import lists
import workerThreadTasks

from logging import getLogger
from simpleDialog import dialog
from win32com.shell import shell, shellcon

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

def makeStringForFalconHelper(string):
	tmp=bytearray(string.encode('UTF-16LE'))
	tmp.extend(b'\x00\x00')
	return bytes(tmp)

def InitContextMenu(wnd):
	falconHelper.initContextMenu(wnd)

def GetContextMenu():
	falconHelper.getContextMenu()

def AddCustomContextMenuItem(name,identifier):
	falconHelper.addCustomContextMenuItem(makeStringForFalconHelper(name),identifier)

def AddContextMenuItemsFromWindows(path):
	path_bytes=makeStringForFalconHelper(json.dumps(path))
	ret=falconHelper.addContextMenuItemsFromWindows(path_bytes)
	return ret==1

def ShowContextMenu(x,y):
	return falconHelper.showContextMenu(x,y)

def ExecContextMenuItem(id):
	falconHelper.execContextMenuItem(id)

def DestroyContextMenu():
	falconHelper.destroyContextMenu()

def ExtractText(path):
	path_bytes=makeStringForFalconHelper(path)
	ptr=falconHelper.extractText(path_bytes)
	s=ctypes.c_char_p(ptr).value
	falconHelper.releasePtr(ptr)
	s2=s.decode('UTF-8')
	return s2

def disableWindowStyleFlag(hwnd,flag):
	"""指定されたウィンドウハンドルの DWL_STYLE の値を撮って、指定されたフラグを折る。"""
	value=win32api.GetWindowLong(hwnd,-16)#-16 が DWL_STYLE らしい
	tmp=0xffffffff-flag
	value=value&tmp
	win32api.SetWindowLong(hwnd,-16,value)

def IteratePaths(path,append_eol=False):
	"""FindFirstFile 系を使って、パス名をイテレートする。append_eol=True にすると、最後に "eol" という1行をリストに入れるので、検索の終了判定などに使える。"""
	try:
		for elem in win32file.FindFilesIterator(os.path.join(path,"*")):
			if elem[8]=="." or elem[8]=="..": continue
			if elem[0]&win32file.FILE_ATTRIBUTE_DIRECTORY: 
				yield from IteratePaths(os.path.join(path,elem[8]))
			#end ディレクトリ
			yield os.path.join(path,elem[8])
		#end iterate
	except pywintypes.error as e:
		log.error("Access denied while searching paths at %s (%s)." % (path,e))
	#end except
	#EOL挿入
	if append_eol: yield "eol"

def GetDirectorySize(path,fileCount=0,dirCount=0):
	"""ディレクトリのサイズをバイト数で返す。"""
	total = 0
	try:
		with os.scandir(path) as it:
			for entry in it:
				if isLink(entry.path):
					print("Synlink skipped:"+entry.path)
					log.debug("Synlink skipped:"+entry.path)
					continue
				elif entry.is_file(follow_symlinks=False):
					total += entry.stat().st_size
					fileCount+=1
				elif entry.is_dir(follow_symlinks=False):
					dirCount+=1
					r=GetDirectorySize(entry.path,fileCount,dirCount)
					if r==(-1,0-1,-1):continue
					total+=r[0]
					fileCount=r[1]
					dirCount=r[2]
	except OSError as er:
		log.error("GetDirectorySize failed (%s" % er)
		return -1,-1,-1
	#end except
	return total,fileCount,dirCount

def GetExecutableState(path):
	"""指定されたファイルパスが、実行可能ファイルであろうかどうかを調べて boolean で返す。"""
	return os.path.splitext(path)[1].upper() in os.environ["pathext"].split(";")

def calcHash(path,algo):
	h = hashlib.new(algo)
	len = hashlib.new(algo).block_size * 0x800
	try:
		with open(path,'rb') as f:
			BinaryData = f.read(len)
			while BinaryData:
				h.update(BinaryData)
				BinaryData = f.read(len)
				return h.hexdigest()
	except:
		return _("エラー")

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

def RunFile(path, admin=False,prm="", workdir=""):
	"""ファイルを起動する。admin=True の場合、管理者として実行する。"""
	path=os.path.expandvars(path)
	msg="running '%s' prm='%s' workdir='%s' asAdmin=%s" % (path,prm,workdir,str(admin))
	log.debug(msg)
	msg=_("管理者で起動") if admin else _("起動")
	globalVars.app.say(msg)
	error=""
	if admin:
		try:
			executable=GetExecutableState(path)
			p=path if executable else "cmd"
			a=prm if executable else "/c \"%s\" %s" % (path,prm)
			ret=shell.ShellExecuteEx(shellcon.SEE_MASK_NOCLOSEPROCESS,0,"runas",p,a,workdir)
		except pywintypes.error as e:
			error=str(e)
		#end shellExecuteEx failure
	else:
		try:
			win32api.ShellExecute(0,"open",path,prm,workdir,1)
		except win32api.error as er:
			error=str(er)
		#end shellExecute failure
	#end admin or not
	if error!="":
		dialog(_("エラー"),_("ファイルを開くことができませんでした(%(error)s)") % {"error": error})
	#end ファイル開けなかった
#end RunFile

def ValidateRegularExpression(exp):
	try:
		test=re.compile(exp)
	except Exception as e:
		return str(e)
	#end error
	return "OK"

def CommandLineToArgv(cmd):
	nargs=ctypes.c_int()
	ctypes.windll.shell32.CommandLineToArgvW.restype=ctypes.POINTER(ctypes.c_wchar_p)
	lpargs=ctypes.windll.shell32.CommandLineToArgvW(cmd,ctypes.byref(nargs))
	args = [lpargs[i] for i in range(nargs.value)]
	if ctypes.windll.kernel32.LocalFree(lpargs):
		raise AssertionError
	#end error
	return args

#渡された拡張子がドキュメント形式であればTrue
def isDocumentExt(ext):
	return ext.lower() in constants.SUPPORTED_DOCUMENT_FORMATS | globalVars.app.documentFormats

def ResolveLocalIpAddress(name):
	addr=""
	try:
		addr=socket.getaddrinfo(name,None)[0][4][0]
	except Exception:
		pass
	#end error
	return addr

def GetNetworkResource(target):
	#targetに指定した名前のネットワークリソースを取得(例：\\network。存在しない場合や何らかのエラー発生時はNoneを返す。)
	try:
		resources=workerThreadTasks.GetNetworkResources()
		for resource in resources:
			if resource.fullpath==target:
				return resource
		log.info("network resource \""+target+"\" not found.")
		return None
	except Exception as e:
		return None

def GetRootObject(rootPath):
	"""
		与えられたパスが示すルートドライブのオブジェクトを返す。
		パスの妥当性・パスが示すアイテムの存在は確認しない。
		DriveまたはNetworkResourceが返る
	"""
	elem=None
	rootPath=rootPath[0]
	if rootPath!="\\":		#\でないならそれはドライブ
		try:
			elem=lists.drive.GetDriveObject(int(ord(rootPath)-65))
		except:
			pass
	else:					#ネットワークリソース
		rootPath=self.listObject.rootDirectory
		rootPath=rootPath[0:rootPath[2:].find("\\")+2]
		elem=misc.GetNetworkResource(rootPath)
	return elem

def PathParamSplit(input):
	"""
		pathとparamがつながった１つのStringをPathとParamに分けて返します。
		windowsの規則に従い、Pathは" "で囲われているか、半角スペースを含まずに記述されている必要があります。
		inputが不正な場合、path,param共にNoneが返ります。
	"""
	if input[0]=="\"":		#" "で囲われた範囲を抽出
		end=input.find("\"",1)
		if end==1 or end==-1:
			return None,None
		path=input[1:end]
		prm=input[end+1:]
		return path,prm
	else:
		end=input.find(" ",0)
		if end<=0:
			return None,None
		path=input[0:end]
		prm=input[end+1:]
		return path,prm

def isLink(path):
	"""
		pathがシンボリックリンクまたはジャンクションならTrue
	"""
	attrs = win32api.GetFileAttributes(path)
	return attrs & win32con.FILE_ATTRIBUTE_REPARSE_POINT!=0

def analyzeUserInputPath(path,parent="C:\\"):
	"""
		ユーザが入力したパスを最適化
		・入力は絶対パスを想定
		・環境変数の展開
		・ドライブ直下以外では末尾の\\を除去
		・相対パスの場合はparentからの絶対パスへ変換
		・C:でもCでもC:\\にする
	"""
	path=os.path.expandvars(path)
	if type(path)!=str:
		return None
	if len(path)==2 and path[0].upper()>='A' and path[0].upper()<='Z' and path[1]==':':
		#アルファベット:はドライブルートと仮定
		return path.upper()+"\\"
	if path=="":
		#空文字はドライブ一覧を示す
		return ""
	else:
		#それ以外
		if os.path.isabs(path):
			return os.path.normpath(path)
		else:
			return os.path.normpath(os.path.join(parent, path))
