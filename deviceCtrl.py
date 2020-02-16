# -*- coding: utf-8 -*-
#Falcon device ctrl
#Copyright (C) 2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import win32file
import winioctlcon
import pywintypes
import ctypes
import re

import errorCodes

from simpleDialog import dialog
from logging import getLogger


log=getLogger("falcon.deviceCtrl")
falconHelper=ctypes.cdll.LoadLibrary("falconHelper.dll")
falconHelper.ejectDevice.argtypes=[ctypes.c_char_p]

def ejectDrive(driveLetter):

	try:
		deviceName=win32file.QueryDosDevice(driveLetter[0].upper()+":")
	except pywintypes.error as e:
		if e.winerror==2:
			return errorCodes.FILE_NOT_FOUND
		else:
			dialog(_("エラー"),e.strerror)
			#log.error(unknown error in"+e.funcname+". code="+e.winerror+" message="+e.strerror)
			return errorCodes.UNKNOWN

	deviceName=re.sub(r"\\Device\\([^\x00]+).*",r"\1",deviceName)

	try:
		handle=win32file.CreateFile(
			"\\\\.\\"+deviceName,
			win32file.GENERIC_WRITE | win32file.GENERIC_READ,
			0,	#クローズするまで他からはOPENできない
			None, #セキュリティ関連の構造体
			win32file.OPEN_EXISTING,	#デバイスのOPENはこれじゃないとダメ
			0, 
			None)
	except pywintypes.error as e:
		if e.winerror==32:
			return errorCodes.ACCESS_DENIED
		else:
			dialog(_("エラー"),e.strerror)
			#log.error(unknown error in"+e.funcname+". code="+e.winerror+" message="+e.strerror)
			return errorCodes.UNKNOWN


	ret=win32file.DeviceIoControl(handle,winioctlcon.IOCTL_DISK_EJECT_MEDIA,None,None)

	handle.Close()

	return errorCodes.OK


def EjectDevice(letter):
	log.debug("Trying to eject drive %s..." % letter)
	ret=falconHelper.ejectDevice(letter.encode('utf-8'))
	if ret==0:
		log.debug("Successfully ejected.")
		return errorCodes.OK
	else:
		log.debug("Failed to eject device (Error code: %d)" % ret)
		return errorCodes.UNKNOWN
