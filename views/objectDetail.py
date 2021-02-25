# -*- coding: utf-8 -*-
#Falcon object detail view
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx

import globalVars
import misc
import views.ViewCreator

from logging import getLogger

from views.baseDialog import *

class Dialog(BaseDialog):
	#計算中のフィールドを表す
	CALCURATING=None

	def __init__(self):
		super().__init__("objectDetailDialog")
		self.task=None
		self.calcuratingFields=[]

	def Initialize(self,dic=None):
		super().Initialize(globalVars.app.hMainView.hFrame,_("詳細情報"))
		self.InstallControls(dic)
		return True

	def InstallControls(self,dic):
		"""いろんなwidgetを設置する。"""
		self.creator=views.ViewCreator.ViewCreator(self.viewMode,self.panel,self.sizer,views.ViewCreator.FlexGridSizer,20)

		if dic:
			for title,content in dic.items():
				self.add(title,content)

		self.buttonArea=views.ViewCreator.ViewCreator(self.viewMode,self.panel,self.sizer,wx.HORIZONTAL,20,style=wx.ALIGN_RIGHT)
		self.bOk=self.buttonArea.okbutton(_("ＯＫ"),None)

	def add(self,title,content):
		if content!=self.CALCURATING:
			f,static=self.creator.inputbox(title,x=400,defaultValue=str(content),style=wx.TE_READONLY)
		else:
			f,static=self.creator.inputbox(title,x=400,defaultValue=_("計算中"),style=wx.TE_READONLY)
			self.calcuratingFields.append(f)

	def Destroy(self):
		if self.task:
			self.task.Cancel()
		super().Destroy()

	def setDirCalcResult(self,results,taskState):
		result=results[0][1]		#2つ以上来ることはなく、パス文字列は不要
		if result[0]>=0:
			self.calcuratingFields[0].SetValue(misc.ConvertBytesTo(result[0],misc.UNIT_AUTO,True))
			self.calcuratingFields[1].SetValue(str(result[0]))
			self.calcuratingFields[2].SetValue(_("ファイル数： %d サブディレクトリ数： %d") % (result[1],result[2]))
		else:
			self.calcuratingFields[0].SetValue(_("不明"))
			self.calcuratingFields[1].SetValue(_("不明"))
			self.calcuratingFields[2].SetValue(_("不明"))
		self.task=None

	def setTask(self,task):
		self.task=task

