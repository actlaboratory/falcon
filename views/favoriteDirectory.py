# -*- coding: utf-8 -*-
#Falcon favoriteDirectory setting view
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import os

import misc
import views.keyConfig
import views.ViewCreator

from .baseDialog import *
from logging import getLogger
from simpleDialog import dialog

class Dialog(BaseDialog):

	def __init__(self,config,keyConfig):
		super().__init__()
		self.config=config
		self.keyConfig=keyConfig

	def Initialize(self):
		t=misc.Timer()
		self.identifier="favoriteDirectoryDialog"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		super().Initialize(self.app.hMainView.hFrame,_("お気に入りディレクトリ"))
		self.InstallControls()
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""

		#情報の表示
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.VERTICAL,20)
		self.hListCtrl=self.creator.ListCtrl(0,wx.ALL|wx.ALIGN_CENTER_HORIZONTAL,size=(750,300),style=wx.LC_REPORT | wx.LC_NO_HEADER | wx.LC_SINGLE_SEL,name=_("現在の登録内容"))

		self.hListCtrl.InsertColumn(0,_("名前"),format=wx.LIST_FORMAT_LEFT,width=200)
		self.hListCtrl.InsertColumn(1,_("場所"),format=wx.LIST_FORMAT_LEFT,width=350)
		self.hListCtrl.InsertColumn(2,_("ショートカット"),format=wx.LIST_FORMAT_LEFT,width=200)

		for name,path in self.config.items():
			self.hListCtrl.Append((name,path,self.keyConfig[name]))

		self.hListCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED,self.ItemSelected)
		self.hListCtrl.Bind(wx.EVT_LIST_ITEM_DESELECTED,self.ItemSelected)

		#処理ボタン
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.creator.GetSizer(),wx.HORIZONTAL,20,"",wx.ALIGN_RIGHT)
		self.addButton=self.creator.button(_("追加"),self.add)
		self.editButton=self.creator.button(_("変更"),self.edit)
		self.editButton.Enable(False)
		self.deleteButton=self.creator.button(_("削除"),self.delete)
		self.deleteButton.Enable(False)

		#ボタンエリア
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.HORIZONTAL,20,"",wx.ALIGN_RIGHT)
		self.bOk=self.creator.okbutton(_("ＯＫ"),None)
		self.bCancel=self.creator.cancelbutton(_("キャンセル"),None)

	def ItemSelected(self,event):
		self.editButton.Enable(self.hListCtrl.GetFocusedItem()>=0)
		self.deleteButton.Enable(self.hListCtrl.GetFocusedItem()>=0)

	def GetData(self):
		return self.config,self.keyConfig


	def add(self,event):
		d=SettingDialog(self.wnd,"","","")
		d.Initialize()
		if d.Show()==wx.ID_CANCEL:
			return
		name,path,key=d.GetValue()
		if name in self.config:	
			dlg=wx.MessageDialog(self.wnd,_("この名前は既に登録されています。登録を上書きしますか？"),_("上書き確認"),wx.YES_NO|wx.ICON_QUESTION)
			if dlg.Show()==wx.ID_NO:
				return
			index=self.hListCtrl.FindItem(-1,name)
			self.hListCtrl.SetItem(index,1,path)
			self.hListCtrl.SetItem(index,2,key)
		else:
			self.hListCtrl.Append((name,path,key))
		self.config[name]=path
		self.keyConfig[name]=key

	def edit(self,event):
		index=self.hListCtrl.GetFocusedItem()
		oldName=self.hListCtrl.GetItemText(index,0)
		path=self.config[oldName]
		key=self.keyConfig[oldName]

		d=SettingDialog(self.wnd,oldName,path,key)
		d.Initialize()
		if d.Show()==wx.ID_CANCEL:
			return
		name,path,key=d.GetValue()
		if oldName!=name and (name in self.config):
			dlg=wx.MessageDialog(self.wnd,_("この名前は既に登録されています。登録を上書きしますか？"),_("上書き確認"),wx.YES_NO|wx.ICON_QUESTION)
			if dlg.ShowModal()==wx.ID_NO:
				return

			del(self.config[oldName])
			del(self.keyConfig[oldName])
			self.hListCtrl.DeleteItem(index)

			index=self.hListCtrl.FindItem(-1,name)
			self.hListCtrl.SetItem(index,1,path)
			self.hListCtrl.SetItem(index,2,key)
		else:
			self.hListCtrl.SetItem(index,0,name)
			self.hListCtrl.SetItem(index,1,path)
			self.hListCtrl.SetItem(index,2,key)

		self.config[name]=path
		self.keyConfig[name]=key

	def delete(self,event):
		index=self.hListCtrl.GetFocusedItem()
		name=self.hListCtrl.GetItemText(index,0)
		del(self.config[name])
		del(self.keyConfig[name])
		self.hListCtrl.DeleteItem(index)

class SettingDialog(BaseDialog):
	"""Dialogの上に作られ、設定内容を入力するダイアログ"""

	def __init__(self,parent,name,path,key):
		self.parent=parent
		self.name=name
		self.path=path
		self.key=key

	def Initialize(self):
		super().Initialize(self.parent,_("登録内容の入力"),style=wx.WS_EX_VALIDATE_RECURSIVELY )
		self.InstallControls()
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""

		#情報の表示
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.VERTICAL,20)
		self.nameEdit,dummy=self.creator.inputbox("名前",500,self.name)
		self.pathEdit,dummy=self.creator.inputbox("パス",500,self.path)
		self.refBtn=self.creator.button("参照",self.getRef,wx.ALIGN_RIGHT)
		self.keyEdit,dummy=self.creator.inputbox("ショートカット",500,self.key,style=wx.TE_READONLY)
		self.refBtn=self.creator.button("設定",self.SetKey,wx.ALIGN_RIGHT)

		#ボタンエリア
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.HORIZONTAL,20,"",wx.ALIGN_RIGHT)
		self.bOk=self.creator.okbutton(_("ＯＫ"),self.OKButtonEvent)
		self.bCancel=self.creator.cancelbutton(_("キャンセル"),None)

	def GetData(self):
		return (self.nameEdit.GetLineText(0),self.pathEdit.GetLineText(0),self.keyEdit.GetLineText(0))

	def getRef(self,event):
		d=wx.DirDialog(self.wnd,"場所の選択",style=wx.DD_DIR_MUST_EXIST | wx.DD_SHOW_HIDDEN)
		if d.Show()==wx.ID_CANCEL:
			return
		self.pathEdit.SetValue(d.GetPath())

	def OKButtonEvent(self,event):
		if self.nameEdit.GetLineText(0)=="" or self.pathEdit.GetLineText(0)=="":
			return
		path=os.path.expandvars(self.pathEdit.GetLineText(0))
		if not os.path.isabs(path):
			dialog(_("エラー"),_("パスは絶対パスで指定してください。"))
			return
		if not os.path.isdir(path):
			dialog(_("エラー"),_("入力されたパスが存在しません。有効なディレクトリへのパスであることを確認してください。"))
			return
		event.Skip()

	def SetKey(self,event):
		d=views.keyConfig.Dialog(self.wnd)
		d.Initialize()
		if d.Show()==wx.ID_CANCEL:
			return

		self.keyEdit.SetValue(d.GetValue())
		globalVars.app.say(_("%s に設定しました。") % (d.GetValue()))
		return
