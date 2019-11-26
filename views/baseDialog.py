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

	def Initialize(self, parent,ttl):
		"""タイトルを指定して、ウィンドウを初期化し、親の中央に配置するように設定。"""

		self.wnd=wx.Dialog(parent,-1, ttl,style=wx.DEFAULT_DIALOG_STYLE)
		self.panel = wx.Panel(self.wnd,wx.ID_ANY)
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.panel.SetSizer(self.sizer)
		self.wnd.Centre()


