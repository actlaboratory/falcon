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
		manager=fontManager()
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
		font=manager.getFont()
		dialog("test",str(font.GetPointSize()))
		dialog("test",font.GetNativeFontInfoUserDesc())
		dialog("test",font.GetNativeFontInfoDesc())

		manager.showSettingDialog(self.hFrame)
		font=manager.getFont()
		dialog("test",str(font.GetPointSize()))
		dialog("test",font.GetNativeFontInfoUserDesc())
		dialog("test",font.GetNativeFontInfoDesc())
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""
		self.creator=views.ViewCreator.ViewCreator(1,self.hFrame)
		self.hButton=self.creator.button("閉じる",self.OnButton)

	def OnButton(self,evt):
		self.hFrame.Destroy()

