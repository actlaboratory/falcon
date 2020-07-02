# -*- coding: utf-8 -*-
#Falcon change file attribute view
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
from logging import getLogger, FileHandler, Formatter
from .baseDialog import *
import keymap
import misc
from simpleDialog import *
import views.ViewCreator


class Dialog(BaseDialog):
	def __init__(self,defaultAttributes):
		super().__init__()
		#現在の属性を初期値としてセット
		self.defaultAttributes=defaultAttributes

	def Initialize(self):
		t=misc.Timer()
		self.identifier="changeAttributeDialog"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		super().Initialize(self.app.hMainView.hFrame,_("属性変更"))
		self.InstallControls()
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""
		self.mainArea=views.ViewCreator.BoxSizer(self.sizer,wx.HORIZONTAL,wx.ALIGN_CENTER)

		#属性の変更
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.mainArea,wx.VERTICAL,20,_("属性の変更"))
		self.checks=self.creator.checkbox3([_("読み取り専用"),_("隠し"),_("システム"),_("アーカイブ")],None,self.defaultAttributes)

		#タイムスタンプの変更
		#self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.mainArea,wx.VERTICAL,20,_("タイムスタンプの変更"))
		#self.date=self.creator.calendar()
		#self.time=self.creator.timepicker()

		self.buttonArea=views.ViewCreator.BoxSizer(self.sizer,wx.HORIZONTAL)
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.buttonArea,wx.HORIZONTAL,20)
		self.bOk=self.creator.okbutton(_("ＯＫ"),None)
		self.bCancel=self.creator.cancelbutton(_("キャンセル"),None)

	def GetData(self):
		v=[]
		v.append(self.checks[0].Get3StateValue())
		v.append(self.checks[1].Get3StateValue())
		v.append(self.checks[2].Get3StateValue())
		v.append(self.checks[3].Get3StateValue())
		return v
