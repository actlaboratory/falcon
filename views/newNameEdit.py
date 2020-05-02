# -*- coding: utf-8 -*-
#Falcon make directory view
#Copyright (C) 2019 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import globalVars
import misc
import views.ViewCreator
from logging import getLogger
from views.baseDialog import *

class Dialog(BaseDialog):
	def Initialize(self,detailText=""):
		t=misc.Timer()
		self.identifier="newNameEditDialog"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		self.app=globalVars.app
		super().Initialize(self.app.hMainView.hFrame,_("新しい名前を入力"))
		self.InstallControls(detailText)
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallControls(self,detailText):
		"""いろんなwidgetを設置する。"""
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.VERTICAL,20)
		if detailText!="":
		detail=self.creator.static
		self.iName,self.static=self.creator.inputbox(_("新しい名前"),400)

		self.buttonArea=views.ViewCreator.BoxSizer(self.sizer,wx.HORIZONTAL, wx.ALIGN_RIGHT)
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.buttonArea,wx.HORIZONTAL,20)
		self.bOk=self.creator.okbutton(_("ＯＫ"),None)
		self.bCancel=self.creator.cancelbutton(_("キャンセル"),None)

	def Show(self):
		result=self.ShowModal()
		self.Destroy()
		return result

	def Destroy(self):
		self.log.debug("destroy")
		self.wnd.Destroy()

	def GetValue(self):
		return self.iName.GetLineText(0)
