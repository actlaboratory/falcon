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

	def Initialize(self, parent,ttl, x, y,px,py):
		"""タイトルとウィンドウサイズとポジションを指定して、ウィンドウを初期化する。"""
		if (x==-1):
			#x=parent.GetPosition().
			x=100
		if (y==-1):
			#y=parent.GetPosition().
			y=100
		self.wnd=wx.Dialog(parent,-1, ttl, size=(x,y),pos=(px,py))



