# -*- coding: utf-8 -*-
#Falcon change file attribute view
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
import ctypes
import gettext
import logging
import os
import sys
import wx
import win32con
import win32gui
from logging import getLogger, FileHandler, Formatter

from .baseDialog import *
import constants
import DefaultSettings
import errorCodes
import globalVars
import keymap
import misc
from simpleDialog import *
import views.ViewCreator

dll=ctypes.cdll.LoadLibrary("whelper.dll")

class Dialog(BaseDialog):
	def Initialize(self):
		t=misc.Timer()
		self.identifier="changeAttributeDialog"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		self.app=globalVars.app
		super().Initialize(self.app.hMainView.hFrame,_("属性変更"),self.app.config.getint(self.identifier,"sizeX"),self.app.config.getint(self.identifier,"sizeY"), self.app.config.getint(self.identifier,"positionX"), self.app.config.getint(self.identifier,"positionY"))
		self.InstallControls()
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""
		self.creator=views.ViewCreator.ViewCreator(1,self.wnd,wx.VERTICAL,20,_("属性の変更"))
		if 1>0:		# TODO:モード設定実装後はここでモード１＝白黒反転の場合のみを指定する
			dll.ScCheckbox(self.creator.getPanel().GetHandle())
		self.cReadonly=self.creator.checkbox(_("読み取り専用"),None)
		self.cHidden=self.creator.checkbox(_("隠し"),None)
		self.cSystem=self.creator.checkbox(_("システム"),None)
		self.cArchive=self.creator.checkbox(_("アーカイブ"),None)
		self.bOk=self.creator.okbutton(_("OK"),None)
		self.bCancel=self.creator.cancelbutton(_("キャンセル"),None)

	def Show(self):
		result=self.wnd.ShowModal()
		self.Destroy()
		self.value=misc.attrib2dward(self.cReadonly.IsChecked(), self.cHidden.IsChecked(), self.cSystem.IsChecked(), self.cArchive.IsChecked())
		return result

	def Destroy(self):
		self.log.debug("destroy")
		self.wnd.Destroy()

	def GetValue(self):
		return self.value

