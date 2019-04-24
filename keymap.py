# -*- coding: utf-8 -*-
#Falcon key map management
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
import configparser
import logging
import os
import wx
import constants
import defaultKeymap
import errorCodes

from simpleDialog import *

str2key={
	"CONTROL_A":wx.WXK_CONTROL_A, 
	"CONTROL_B":wx.WXK_CONTROL_B,
	"CONTROL_C":wx.WXK_CONTROL_C,
	"CONTROL_D":wx.WXK_CONTROL_D,
	"CONTROL_E":wx.WXK_CONTROL_E,
	"CONTROL_F":wx.WXK_CONTROL_F,
	"CONTROL_G":wx.WXK_CONTROL_G,
	"CONTROL_H":wx.WXK_CONTROL_H,
	"CONTROL_I":wx.WXK_CONTROL_I,
	"CONTROL_J":wx.WXK_CONTROL_J,
	"CONTROL_K":wx.WXK_CONTROL_K, 
	"CONTROL_L":wx.WXK_CONTROL_L,
	"CONTROL_M":wx.WXK_CONTROL_M,
	"CONTROL_N":wx.WXK_CONTROL_N,
	"CONTROL_O":wx.WXK_CONTROL_O,
	"CONTROL_P":wx.WXK_CONTROL_P,
	"CONTROL_Q":wx.WXK_CONTROL_Q,
	"CONTROL_R":wx.WXK_CONTROL_R,
	"CONTROL_S":wx.WXK_CONTROL_S,
	"CONTROL_T":wx.WXK_CONTROL_T,
	"CONTROL_U":wx.WXK_CONTROL_U, 
	"CONTROL_V":wx.WXK_CONTROL_V,
	"CONTROL_W":wx.WXK_CONTROL_W,
	"CONTROL_X":wx.WXK_CONTROL_X,
	"CONTROL_Y":wx.WXK_CONTROL_Y,
	"CONTROL_Z":wx.WXK_CONTROL_Z,

	"BACK":wx.WXK_BACK,
	"TAB":wx.WXK_TAB,
	"RETURN":wx.WXK_RETURN,
	"ESCAPE":wx.WXK_ESCAPE, 
	"SPACE":wx.WXK_SPACE,
	"DELETE":wx.WXK_DELETE,
	"START":wx.WXK_START,
	"LBUTTON":wx.WXK_LBUTTON,
	"RBUTTON":wx.WXK_RBUTTON,
	"CANCEL":wx.WXK_CANCEL,
	"MBUTTON":wx.WXK_MBUTTON,
	"CLEAR":wx.WXK_CLEAR,
	"SHIFT":wx.WXK_SHIFT,
	"ALT":wx.WXK_ALT, 
	"CONTROL":wx.WXK_CONTROL,
	"RAW_CONTROL":wx.WXK_RAW_CONTROL,
	"MENU":wx.WXK_MENU,
	"PAUSE":wx.WXK_PAUSE,
	"CAPITAL":wx.WXK_CAPITAL,
	"END":wx.WXK_END,
	"HOME":wx.WXK_HOME,
	"LEFT":wx.WXK_LEFT,
	"UP":wx.WXK_UP,
	"RIGHT":wx.WXK_RIGHT, 
	"DOWN":wx.WXK_DOWN,
	"SELECT":wx.WXK_SELECT,
	"PRINT":wx.WXK_PRINT,
	"EXECUTE":wx.WXK_EXECUTE,
	"SNAPSHOT":wx.WXK_SNAPSHOT,
	"INSERT":wx.WXK_INSERT,
	"HELP":wx.WXK_HELP,

	"NUMPAD0":wx.WXK_NUMPAD0,
	"NUMPAD1":wx.WXK_NUMPAD1,
	"NUMPAD2":wx.WXK_NUMPAD2, 
	"NUMPAD3":wx.WXK_NUMPAD3,
	"NUMPAD4":wx.WXK_NUMPAD4,
	"NUMPAD5":wx.WXK_NUMPAD5,
	"NUMPAD6":wx.WXK_NUMPAD6,
	"NUMPAD7":wx.WXK_NUMPAD7,
	"NUMPAD8":wx.WXK_NUMPAD8,
	"NUMPAD9":wx.WXK_NUMPAD9,

	"MULTIPLY":wx.WXK_MULTIPLY,
	"ADD":wx.WXK_ADD,
	"SEPARATOR":wx.WXK_SEPARATOR, 
	"SUBTRACT":wx.WXK_SUBTRACT,
	"DECIMAL":wx.WXK_DECIMAL,
	"DIVIDE":wx.WXK_DIVIDE,

	"F1":wx.WXK_F1,
	"F2":wx.WXK_F2,
	"F3":wx.WXK_F3,
	"F4":wx.WXK_F4,
	"F5":wx.WXK_F5,
	"F6":wx.WXK_F6,
	"F7":wx.WXK_F7, 
	"F8":wx.WXK_F8,
	"F9":wx.WXK_F9,
	"F10":wx.WXK_F10,
	"F11":wx.WXK_F11,
	"F12":wx.WXK_F12,
	"F13":wx.WXK_F13,
	"F14":wx.WXK_F14,
	"F15":wx.WXK_F15,
	"F16":wx.WXK_F16,
	"F17":wx.WXK_F17, 
	"F18":wx.WXK_F18,
	"F19":wx.WXK_F19,
	"F20":wx.WXK_F20,
	"F21":wx.WXK_F21,
	"F22":wx.WXK_F22,
	"F23":wx.WXK_F23,
	"F24":wx.WXK_F24,

	"NUMLOCK":wx.WXK_NUMLOCK,
	"SCROLL":wx.WXK_SCROLL,
	"PAGEUP":wx.WXK_PAGEUP, 
	"PAGEDOWN":wx.WXK_PAGEDOWN,
	"NUMPAD_SPACE":wx.WXK_NUMPAD_SPACE,
	"NUMPAD_TAB":wx.WXK_NUMPAD_TAB,
	"NUMPAD_ENTER":wx.WXK_NUMPAD_ENTER,

	"NUMPAD_F1":wx.WXK_NUMPAD_F1,
	"NUMPAD_F2":wx.WXK_NUMPAD_F2,
	"NUMPAD_F3":wx.WXK_NUMPAD_F3,
	"NUMPAD_F4":wx.WXK_NUMPAD_F4,

	"NUMPAD_HOME":wx.WXK_NUMPAD_HOME,
	"NUMPAD_LEFT":wx.WXK_NUMPAD_LEFT, 
	"NUMPAD_UP":wx.WXK_NUMPAD_UP,
	"NUMPAD_RIGHT":wx.WXK_NUMPAD_RIGHT,
	"NUMPAD_DOWN":wx.WXK_NUMPAD_DOWN,
	"NUMPAD_PAGEUP":wx.WXK_NUMPAD_PAGEUP,
	"NUMPAD_PAGEDOWN":wx.WXK_NUMPAD_PAGEDOWN,
	"NUMPAD_END":wx.WXK_NUMPAD_END,
	"NUMPAD_BEGIN":wx.WXK_NUMPAD_BEGIN,
	"NUMPAD_INSERT":wx.WXK_NUMPAD_INSERT,
	"NUMPAD_DELETE":wx.WXK_NUMPAD_DELETE,
	"NUMPAD_EQUAL":wx.WXK_NUMPAD_EQUAL, 
	"NUMPAD_MULTIPLY":wx.WXK_NUMPAD_MULTIPLY,
	"NUMPAD_ADD":wx.WXK_NUMPAD_ADD,
	"NUMPAD_SEPARATOR":wx.WXK_NUMPAD_SEPARATOR,
	"NUMPAD_SUBTRACT":wx.WXK_NUMPAD_SUBTRACT,
	"NUMPAD_DECIMAL":wx.WXK_NUMPAD_DECIMAL,
	"NUMPAD_DIVIDE":wx.WXK_NUMPAD_DIVIDE,

	"WINDOWS_LEFT":wx.WXK_WINDOWS_LEFT,
	"WINDOWS_RIGHT":wx.WXK_WINDOWS_RIGHT,
	"WINDOWS_MENU":wx.WXK_WINDOWS_MENU,
	"COMMAND":wx.WXK_COMMAND, 

	"A": ord('A'),
	"B": ord('B'),
	"C": ord('C'),
	"D": ord('D'),
	"E": ord('E'),
	"F": ord('F'),
	"G": ord('G'),
	"H": ord('H'),
	"I": ord('I'),
	"J": ord('J'),
	"K": ord('K'),
	"L": ord('L'),
	"M": ord('M'),
	"N": ord('N'),
	"O": ord('O'),
	"P": ord('P'),
	"Q": ord('Q'),
	"R": ord('R'),
	"S": ord('S'),
	"T": ord('T'),
	"U": ord('U'),
	"V": ord('V'),
	"W": ord('W'),
	"X": ord('X'),
	"Y": ord('Y'),
	"Z": ord('Z'), 
}

class KeymapHandler():
	"""キーマップは、設定ファイルを読んで、wxのアクセラレーターテーブルを生成します。"""
	def __init__(self):
		self.log=logging.getLogger("falcon.keymapHandler")

	def __del__(self):
		pass

	def Initialize(self, filename):
		"""キーマップ情報を初期かします。デフォルトキーマップを適用してから、指定されたファイルを読もうと試みます。ファイルが見つからなかった場合は、FILE_NOT_FOUND を返します。ファイルがパースできなかった場合は、PARSING_FAILED を返します。いずれの場合も、デフォルトキーマップは適用されています。"""
		self.map=configparser.ConfigParser(defaultKeymap.defaultKeymap)
		if not os.path.exists(filename):
			self.log.warning("Cannot find %s" % filename)
			return errorCodes.FILE_NOT_FOUND
		ret=self.map.read(filename, encoding="UTF-8")
		ret= errorCodes.OK if len(ret)>0 else errorCodes.PARSING_FAILED
		if ret==errorCodes.PARSING_FAILED:
			self.log.warning("Cannot parse %s" % filename)
		return ret

	def GenerateTable(self):
		"""アクセラレーターテーブルを生成します。"""
		tbl=[]
		commands=self.map.items("keymap")
		for elem in commands:
			key=elem[1].upper()
			flags=0
			ctrl="CTRL+" in key
			alt="ALT+" in key
			shift="SHIFT+" in key
			codestr=key.split("+")
			if ctrl: flags=wx.ACCEL_CTRL
			if alt: flags=flags|wx.ACCEL_ALT
			if shift: flags=flags|wx.ACCEL_SHIFT

			entry=wx.AcceleratorEntry(flags,str2key[codestr[len(codestr)-1]],constants.MENU_ITEMS[elem[0].upper()])
			tbl.append(entry)
		#end 追加
		return wx.AcceleratorTable(tbl)
