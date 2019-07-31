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
import _winxptheme
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

class Dialog(BaseDialog):
	def Initialize(self):
		t=misc.Timer()
		self.identifier="changeAttributeDialog"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		self.app=globalVars.app
		super().Initialize(_("属性変更"),self.app.config.getint(self.identifier,"sizeX"),self.app.config.getint(self.identifier,"sizeY"), self.app.config.getint(self.identifier,"positionX"), self.app.config.getint(self.identifier,"positionY"))
		self.InstallControls()
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""
		self.creator=views.ViewCreator.ViewCreator(1,self.wnd)
		self.cReadonly=self.creator.checkbox(_("読み取り専用"),None)
		self.cHidden=self.creator.checkbox(_("隠し"),None)
		self.cSystem=self.creator.checkbox(_("システム"),None)
		self.cArchive=self.creator.checkbox(_("アーカイブ"),None)
		self.bOk=self.creator.okbutton(_("OK"),None)
		self.bCancel=self.creator.cancelbutton(_("キャンセル"),None)
		self.sizer=wx.BoxSizer(wx.HORIZONTAL)
		self.sizer.Add(self.cReadonly)
		self.sizer.Add(self.cHidden)
		self.sizer.Add(self.cSystem)
		self.sizer.Add(self.cArchive)
		self.sizer.Add(self.bOk)
		self.sizer.Add(self.bCancel)
		self.creator.getPanel().SetSizer(self.sizer)

	def Show(self):
		return self.wnd.ShowModal()

	def Destroy(self):
		self.wnd.Destroy()

	def GetValue(self):
		return misc.attrib2dward(self.cReadonly.IsChecked(), self.cHidden.IsChecked(), self.cSystem.IsChecked(), self.cArchive.IsChecked())


