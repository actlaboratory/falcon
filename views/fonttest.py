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

class View(BaseView):
	def Initialize(self):
		t=misc.Timer()
		self.identifier="wxFontTestView"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		self.app=globalVars.app
		super().Initialize("wxテスト",800,600)
		self.InstallControls()
		self.hFrame.Show()
		fontchooser=wx.FontDialog(self.hFrame)#第2パラにフォントデータを指定しても良い。デフォルトとして使われる。
		ret=fontchooser.ShowModal()
		s="OK" if ret==wx.ID_OK else "cancel"
		dialog("result",s)
		fontData=fontchooser.GetFontData()#wx.FontDataがとれる
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""
		self.creator=views.ViewCreator.ViewCreator(1,self.hFrame)
		self.hButton=self.creator.button("閉じる",self.OnButton)

	def OnButton(self,evt):
		self.hFrame.Destroy()

