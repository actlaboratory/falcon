# -*- coding: utf-8 -*-
#Falcon app dialogs base class
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import constants
import globalVars
import _winxptheme

class BaseDialog(object):
	"""falconのモーダルダイアログの基本クラス。"""
	def __init__(self):
		self.app=globalVars.app
		self.value=None

	def Initialize(self, parent,ttl,style=wx.DEFAULT_DIALOG_STYLE):
		"""タイトルを指定してウィンドウを初期化"""
		self.wnd=wx.Dialog(parent,-1, ttl,style= wx.CAPTION | wx.SYSTEM_MENU | wx.BORDER_DEFAULT | style)
		_winxptheme.SetWindowTheme(self.wnd.GetHandle(),"","")

		self.wnd.Bind(wx.EVT_CLOSE,self.OnClose)

		self.panel = wx.Panel(self.wnd,wx.ID_ANY)
		self.sizer = wx.BoxSizer(wx.VERTICAL)
		self.panel.SetSizer(self.sizer)

	#ウィンドウを中央に配置してモーダル表示する
	#ウィンドウ内の部品を全て描画してから呼び出す
	def Show(self):
		self.panel.Layout()
		self.sizer.Fit(self.wnd)
		self.wnd.Centre()
		result=self.wnd.ShowModal()
		if result!=wx.ID_CANCEL:
			self.value=self.GetData()
		self.Destroy()
		return result

	def GetValue(self):
		return self.value

	def GetData(self):
		return None		#利用するクラスでオーバーライドする

	def Destroy(self):
		try:		#logのないウィンドウがあるため必要
			self.log.debug("destroy")
		except AttributeError:
			pass
		self.wnd.Destroy()

	#closeイベントで呼ばれる。Alt+F4対策
	def OnClose(self,event):
		if self.wnd.GetWindowStyleFlag() | wx.CLOSE_BOX==wx.CLOSE_BOX:
			self.Destroy()
		else:
			event.Veto()

