# -*- coding: utf-8 -*-
#Falcon Symple imput dialog view
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import misc
import views.ViewCreator
from logging import getLogger
from views.baseDialog import *

class Dialog(BaseDialog):
	def __init__(self,title,detail,parent=None):
		super().__init__("SympleImputDialog")
		self.title=title
		self.detail=detail
		if parent!=None:
			self.parent=None
		else:
			self.parent=self.app.hMainView.hFrame

	def Initialize(self):
		self.log.debug("created")
		super().Initialize(self.parent,self.title)
		self.InstallControls()
		self.log.debug("Finished creating view - %s" % self.title)
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.VERTICAL,20,style=wx.EXPAND)
		self.edit,self.static=self.creator.inputbox(self.detail,-1)

		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.HORIZONTAL,20)
		self.bOk=self.creator.okbutton(_("ＯＫ"),None)
		self.bCancel=self.creator.cancelbutton(_("キャンセル"),None)

	def GetData(self):
		return self.edit.GetLineText(0)
