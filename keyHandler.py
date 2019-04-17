# -*- coding: utf-8 -*-
#Falcon key map management
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
import wx
import logging
import errorCodes
import keymap
from simpleDialog import *

class KeyHandler():
	"""キーハンドラは、wxのイベントを受け取って処理します。"""
	def __init__(self):
		self.log=logging.getLogger("falcon.keyHandler")

	def __del__(self):
		pass

	def Initialize(self, filename):
		"""キーマップを読み込んで準備します。"""
		self.map=keymap.KeymapHandler()
		self.map.Initialize(constants.KEYMAP_FILE_NAME)
		self.ctrlPressed=False
		self.shiftPressed=False

	def ProcessKeyUp(self,evt):
		keycode=evt.GetKeyCode()
		if keycode==WXK_LCONTROL || keycode==WXK_RCONTROL: self.ctrlPressed=False
		if keycode==WXK_LSHIFT || keycode==WXK_RSHIFT: self.ctrlPressed=False

	def ProcessKeyDown(self,evt):
		keycode=evt.GetKeyCode()
		if keycode==WXK_LCONTROL || keycode==WXK_RCONTROL:
			self.ctrlPressed=False
			return
		if keycode==WXK_LSHIFT || keycode==WXK_RSHIFT:
			self.ctrlPressed=True
			return
		#end ctrl か shift
		cmd=self.map.GenerateCommand(keycode,self.ctrlPressed,self.shiftPressed)
		if cmd is not None: dialog("test",cmd)

