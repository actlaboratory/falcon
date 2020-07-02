# -*- coding: utf-8 -*-
#Falcon register originalAssociation view
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import os
import re
from logging import getLogger

from .baseDialog import *
import misc
import views.ViewCreator
from simpleDialog import dialog

class Dialog(BaseDialog):

	def __init__(self,config):
		super().__init__()
		self.config=config

	def Initialize(self):
		t=misc.Timer()
		self.identifier="registOriginalAssociationDialog"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		super().Initialize(self.app.hMainView.hFrame,_("拡張子の独自関連付け"))
		self.InstallControls()
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""

		#情報の表示
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.VERTICAL,20)
		self.hListCtrl=self.creator.ListCtrl(0,wx.ALL|wx.ALIGN_CENTER_HORIZONTAL,size=(600,300),style=wx.LC_REPORT | wx.LC_NO_HEADER | wx.LC_SINGLE_SEL,name=_("現在の登録内容"))

		self.hListCtrl.InsertColumn(0,_("種類"),format=wx.LIST_FORMAT_LEFT,width=250)
		self.hListCtrl.InsertColumn(1,_("実行ファイル名"),format=wx.LIST_FORMAT_LEFT,width=350)

		for i in self.config.items():
			self.hListCtrl.Append((i[0],os.path.basename(os.path.dirname(i[1]))+"\\"+os.path.basename(i[1])))

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
		return self.config


	def add(self,event):
		d=SettingDialog(self.wnd,"","")
		d.Initialize()
		d.Show()
		ext,path=d.GetValue()
		if ext in self.config:	
			dlg=wx.MessageDialog(self.wnd,_("この拡張子は既に登録されています。登録を上書きしますか？"),_("上書き確認"),wx.YES_NO|wx.ICON_QUESTION)
			if dlg.ShowModal()==wx.ID_NO:
				return
			index=self.hListCtrl.FindItem(-1,ext)
			self.hListCtrl.SetItem(index,1,os.path.basename(os.path.dirname(path))+"\\"+os.path.basename(path))
		else:
			self.hListCtrl.Append((ext,os.path.basename(os.path.dirname(path))+"\\"+os.path.basename(path)))
		self.config[ext]=path

	def edit(self,event):
		index=self.hListCtrl.GetFocusedItem()
		ext=self.hListCtrl.GetItemText(index,0)
		path=self.config[ext]

		d=SettingDialog(self.wnd,ext,path)
		d.Initialize()
		d.Show()
		ext,path=d.GetValue()
		self.hListCtrl.SetItem(index,1,os.path.basename(os.path.dirname(path))+"\\"+os.path.basename(path))
		self.config[ext]=path
		d.Destroy()

	def delete(self,event):
		index=self.hListCtrl.GetFocusedItem()
		ext=self.hListCtrl.GetItemText(index,0)
		if "<default" in ext:
			dialog(_("エラー"),_("デフォルト設定は削除できません。"))
			return
		del(self.config[ext])
		self.hListCtrl.DeleteItem(index)

class SettingDialog(BaseDialog):
	"""Dialogの上に作られ、各拡張子と実行ファイルの関連付けを入力するダイアログ"""

	def __init__(self,parent,extention,path):
		self.parent=parent
		self.extention=extention
		self.path=path

	def Initialize(self):
		super().Initialize(self.parent,_("登録内容の入力"),style=wx.WS_EX_VALIDATE_RECURSIVELY )
		self.InstallControls()
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""

		#情報の表示
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.VERTICAL,20)
		if self.extention=="":
			self.extensionEdit,dummy=self.creator.inputbox("拡張子",300,self.extention)
		else:
			self.extensionEdit,dummy=self.creator.inputbox("拡張子",300,self.extention,style=wx.TE_READONLY)
		self.pathEdit,dummy=self.creator.inputbox("実行ファイル名",475,self.path)
		self.refBtn=self.creator.button("参照",self.getRef,wx.ALIGN_RIGHT)

		#ボタンエリア
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.HORIZONTAL,20,"",wx.ALIGN_RIGHT)
		self.bOk=self.creator.okbutton(_("ＯＫ"),self.OKButtonEvent)
		self.bCancel=self.creator.cancelbutton(_("キャンセル"),None)

	def GetData(self):
		return (self.extensionEdit.GetLineText(0).lower(),os.path.abspath(self.pathEdit.GetLineText(0)))

	def getRef(self,event):
		pathext=os.getenv("pathext").replace(";",";*")
		d=wx.FileDialog(self.wnd,"実行ファイルの選択",wildcard="実行ファイル("+pathext+")",style=wx.FD_FILE_MUST_EXIST | wx.FD_SHOW_HIDDEN)
		if d.ShowModal()==wx.ID_CANCEL:
			return
		self.pathEdit.SetValue(d.GetPath())

	def OKButtonEvent(self,event):
		if self.extensionEdit.GetLineText(0)=="" or self.pathEdit.GetLineText(0)=="":
			return
		if not re.match("^[a-zA-Z0-9\\-$~]+$",self.extensionEdit.GetLineText(0)):
			dialog(_("エラー"),_("入力された拡張子に利用できない文字が含まれています。パスを確認してください。"))
			return
		if not os.path.isfile(self.pathEdit.GetLineText(0)):
			dialog(_("エラー"),_("入力された実行ファイルが存在しません。パスを確認してください。"))
			return
		event.Skip()
