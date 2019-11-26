# -*- coding: utf-8 -*-
#Falcon change file attribute view
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
		super().Initialize(self.app.hMainView.hFrame,_("属性変更"),self.app.config.getint(self.identifier,"sizeX"),self.app.config.getint(self.identifier,"sizeY"), self.app.config.getint(self.identifier,"positionX"), self.app.config.getint(self.identifier,"positionY"))
		self.InstallControls()
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""
		self.mainArea=views.ViewCreator.BoxSizer(self.sizer,wx.HORIZONTAL,wx.ALIGN_CENTER)

		#現在の属性を初期値としてセット
		defaultAttributes=globalVars.app.hMainView.activeTab.GetSelectedItems().GetAttributeCheckState()

		#属性の変更
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.mainArea,wx.VERTICAL,20,_("属性の変更"))
		self.checks=self.creator.checkbox3([_("読み取り専用"),_("隠し"),_("システム"),_("アーカイブ")],None,defaultAttributes)

		#タイムスタンプの変更
		#self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.mainArea,wx.VERTICAL,20,_("タイムスタンプの変更"))
		#self.date=self.creator.calendar()
		#self.time=self.creator.timepicker()

		self.buttonArea=views.ViewCreator.BoxSizer(self.sizer,wx.HORIZONTAL)
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.buttonArea,wx.HORIZONTAL,20)
		self.bOk=self.creator.okbutton(_("ＯＫ"),None)
		self.bCancel=self.creator.cancelbutton(_("キャンセル"),None)

		self.sizer.Fit(self.wnd)


	def Show(self):
		result=self.wnd.ShowModal()
		self.Destroy()
		return result

	def Destroy(self):
		self.log.debug("destroy")
		self.wnd.Destroy()

	def GetValue(self):
		v=[]
		v.append(self.checks[0].Get3StateValue())
		v.append(self.checks[1].Get3StateValue())
		v.append(self.checks[2].Get3StateValue())
		v.append(self.checks[3].Get3StateValue())
		return v


