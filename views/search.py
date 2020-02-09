# -*- coding: utf-8 -*-
#Falcon search view
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
from logging import getLogger, FileHandler, Formatter
from .baseDialog import *
import globalVars
import misc
import views.ViewCreator

class Dialog(BaseDialog):

	#検索の起点を設定
	def __init__(self,basePath):
		self.basePath=basePath

	def Initialize(self):
		t=misc.Timer()
		self.identifier="SearchDialog"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		self.app=globalVars.app
		super().Initialize(self.app.hMainView.hFrame,_("検索"))
		self.InstallControls()
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.HORIZONTAL,20,"",wx.EXPAND)
		self.keyword,tmp=self.creator.inputbox(_("キーワード")+"：",500,"")

		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.HORIZONTAL,20,"",wx.EXPAND)
		self.type=self.creator.radiobox(_("検索方式"),(_("通常"),_("grep")),None,1,wx.HORIZONTAL)
		self.keywordType=self.creator.checkbox(_("正規表現を利用"),None,False)

		#ボタンエリア
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.HORIZONTAL,20,"",wx.ALIGN_RIGHT)
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
		v={}
		v["basePath"]=self.basePath
		v["keyword"]=self.keyword.GetLineText(0)
		v["type"]=self.type.GetSelection()
		v["isRegularExpression"]=self.keywordType.IsChecked()
		return v
