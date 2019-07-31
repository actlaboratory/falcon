# -*- coding: utf-8 -*-
#Falcon app dialogs base class
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import constants
import globalVars

class BaseDialog(object):
	"""falconのモーダルダイアログの基本クラス。"""
	def __init__(self):
		pass

	def Initialize(self, ttl, x, y,px,py):
		"""タイトルとウィンドウサイズとポジションを指定して、ウィンドウを初期化する。"""
		self.wnd=wx.Dialog(None,-1, ttl, size=(x,y),pos=(px,py))



