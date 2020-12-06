# -*- coding: utf-8 -*-
#Falcon make directory view
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import views.ViewCreator
from logging import getLogger
from views.baseDialog import *

class Dialog(BaseDialog):
	def __init__(self):
		super().__init__("newNameEditDialog")

	def Initialize(self,detailText=""):
		super().Initialize(self.app.hMainView.hFrame,_("新しい名前を入力"))
		self.InstallControls(detailText)
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


	def GetData(self):
		return self.iName.GetLineText(0)
