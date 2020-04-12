# -*- coding: utf-8 -*-
#Falcon operation Selecter view
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import gettext
from logging import getLogger

from .baseDialog import *
import constants
import errorCodes
import globalVars
import misc
import views.ViewCreator

class Dialog(BaseDialog):

	def __init__(self,info,choices,enableCancel=False):
		self.info=info
		self.choices=choices
		self.enableCancel=enableCancel

	def Initialize(self):
		t=misc.Timer()
		self.identifier="OperationSelecterDialog"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		self.app=globalVars.app
		super().Initialize(self.app.hMainView.hFrame,_("ファイル操作確認"))
		self.InstallControls()
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""

		#情報の表示
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.VERTICAL,20)
		self.hListCtrl=self.creator.ListCtrl(0,wx.ALL|wx.ALIGN_CENTER_HORIZONTAL,size=(600,300),style=wx.LC_REPORT | wx.LC_NO_HEADER | wx.LC_SINGLE_SEL,name=_("アイテム情報"))

		i=0
		for i in range(len(self.info[0])):
			self.hListCtrl.InsertColumn(i,"")

		#for elem in colums():
		#	if count(self.info[0])>i:
		#	self.hListCtrl.InsertColumn(i,elem)
		#	i+=1

		for elem in self.info:
			self.hListCtrl.Append(elem)


		#処理の選択
		self.select=self.creator.radiobox(_("アクション"),list(self.choices.keys()),None,0,wx.VERTICAL)
		self.check=self.creator.checkbox(_("以降も同様に処理する"),None,False)

		#ボタンエリア
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.HORIZONTAL,20,"",wx.ALIGN_RIGHT)
		self.bOk=self.creator.okbutton(_("ＯＫ"),None)
		if self.enableCancel:
			self.bCancel=self.creator.cancelbutton(_("キャンセル"),None)

	def Show(self):
		result=self.ShowModal()
		self.Destroy()
		return result

	def Destroy(self):
		self.log.debug("destroy")
		self.wnd.Destroy()

	def GetValue(self):
		return {
			"response" : self.choices[self.select.GetStringSelection()],
			"all" : self.check.IsChecked()
		}


def GetMethod(request):
	methods={}
	methods["ALREADY_EXISTS"]={
		_("上書きする"):"overwrite",
		_("スキップ"):"skip"
	}
	return methods[request]

