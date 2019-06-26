# -*- coding: utf-8 -*-
#Falcon wx test view
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import gettext
import logging
import os
import sys
import wx
import win32con
import win32gui
from logging import getLogger, FileHandler, Formatter
from .base import *
import constants
import DefaultSettings
import errorCodes
import globalVars
import keymap
import misc
from simpleDialog import *
import views.ViewCreator
from .fontManager import *



class View(BaseView):
	def Initialize(self):
		t=misc.Timer()
		self.identifier="wxFontTestView"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		self.app=globalVars.app
		super().Initialize("wxテスト",800,600)
		manager=FontManager()
		self.InstallControls()
		self.hFrame.Show()

		"""
		# FontDataを生成し、設定を行う
		fontData=wx.FontData()
		fontData.EnableEffects(False)		#取り消し線などは設定できない
		fontData.SetAllowSymbols(False)		#シンボルフォントの設定は認めない
		fontData.SetRange(5,35)
		fontchooser=wx.FontDialog(self.hFrame,fontData)
		fontchooser.ShowModal()
		font=fontchooser.GetFontData().GetChosenFont()
		if not font.IsOk():
			dialog("エラー","有効なフォントではありません。")
			return True
		#アサーションエラーの対策
		"""
		font=manager.GetFont()

		manager.ShowSettingDialog(self.hFrame)
		font=manager.GetFont()
		dialog("test",str(manager.GetSize()))
		dialog("test",manager.GetName())
		globalVars.app.config["view"]["font"]=manager.GetInfo()
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""
		self.creator=views.ViewCreator.ViewCreator(1,self.hFrame)
		self.hButton=self.creator.button("閉じる",self.OnButton)

	def OnButton(self,evt):
		self.hFrame.Destroy()

