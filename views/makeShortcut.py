# -*- coding: utf-8 -*-
#Falcon make Shortcut view
#Copyright (C) 2019 yamahubuki <itiro.ishino@gmail.com>
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
import errorCodes
import globalVars
import keymap
import misc
from simpleDialog import *
import views.ViewCreator

class Dialog(BaseDialog):

	TYPE_LNK=0
	TYPE_HARDLINK=1
	TYPE_SYNLINK=2

	LINK_ABSOLUTE=0
	LINK_RELATIVE=1

	#作成先初期値を決めるためのターゲットの名前とタイプ
	def __init__(self,targetName):
		#対象オブジェクトの拡張子を除く名前
		self.targetName=targetName

	def Initialize(self):
		t=misc.Timer()
		self.identifier="MakeShortcutDialog"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		self.app=globalVars.app
		super().Initialize(self.app.hMainView.hFrame,_("ショートカットの作成"))
		self.InstallControls()
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallControls(self):
		#ここを並び替えるとこのクラス内の色んな所に影響するので注意！
		_typeChoices=[_("ショートカット(lnk)"),_("ハードリンク"),_("シンボリックリンク")]

		"""いろんなwidgetを設置する。"""
		self.mainArea=views.ViewCreator.BoxSizer(self.sizer,wx.HORIZONTAL,wx.ALIGN_CENTER)

		#種類の設定
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.mainArea,wx.VERTICAL,20)
		self.type=self.creator.radiobox(_("作成方式"),_typeChoices,self.typeChangeEvent,1,wx.VERTICAL)

		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.HORIZONTAL,0,"",wx.EXPAND)
		self.destination,tmp=self.creator.inputbox(_("作成先")+"：",-1,self.targetName+".lnk")

		#詳細設定
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.mainArea,wx.VERTICAL,20)
		self.parameter,tmp=self.creator.inputbox(_("パラメータ"),400)
		self.directory,tmp=self.creator.inputbox(_("作業ディレクトリ"),400)
		self.linkType=self.creator.radiobox(_("リンクの種類"),[_("絶対"),_("相対")],None,1,wx.HORIZONTAL)

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
		v["type"]=self.type.GetSelection()
		v["destination"]=self.destination.GetLineText(0)
		v["parameter"]=self.parameter.GetLineText(0)
		v["directory"]=self.directory.GetLineText(0)
		if not v["type"]==self.TYPE_HARDLINK:
			v["linkType"]=self.linkType.GetSelection()
		return v

	#作成するショートカットタイプの変更
	def typeChangeEvent(self,event):
		if (event.GetInt()==self.TYPE_HARDLINK):
			#ハードリンクに絶対・相対の選択はない
			self.linkType.Disable()
		else:
			#ハードリンク以外であれば絶対・相対の選択がある
			self.linkType.Enable()
