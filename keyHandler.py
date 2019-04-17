# -*- coding: utf-8 -*-
#Falcon key map management
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
import wx
import logging

import constants
import errorCodes
import keymap
from simpleDialog import *

class KeyHandler():
	"""キーハンドラは、wxのイベントを受け取って処理します。"""
	def __init__(self):
		self.log=logging.getLogger("falcon.keyHandler")

	def __del__(self):
		pass

	def Initialize(self):
		"""キーマップを読み込んで準備します。"""
		self.map=keymap.KeymapHandler()
		self.map.Initialize(constants.KEYMAP_FILE_NAME)

	def ProcessKeyDown(self,evt):
		keycode=evt.GetKeyCode()
		if keycode in (wx.WXK_CONTROL, wx.WXK_SHIFT): return
		cmd=self.map.GenerateCommand(keycode,wx.GetKeyState(wx.WXK_CONTROL),wx.GetKeyState(wx.WXK_SHIFT))
		if cmd is not None: dialog("test",cmd)

