# -*- coding: utf-8 -*-
#Falcon favoriteDirectory setting view
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import copy
import os
import wx

import globalVars

import views.keyConfig
import views.KeyValueSettingDialogBase

from simpleDialog import dialog

class Dialog(views.KeyValueSettingDialogBase.KeyValueSettingDialogBase):
	def __init__(self,config,keyConfig):
		info=[
			(_("登録名"),wx.LIST_FORMAT_LEFT,200),
			(_("場所"),wx.LIST_FORMAT_LEFT,350),
			(_("ショートカット"),wx.LIST_FORMAT_LEFT,200)
		]
		super().__init__("favoriteDirectoryDialog",SettingDialog,info,config,keyConfig)
		self.oldKeyConfig=copy.copy(keyConfig)

	def Initialize(self):
		return super().Initialize(self.app.hMainView.hFrame,_("お気に入りディレクトリの設定"))

	def OkButtonEvent(self,event):
		"""
			設定されたキーが重複している場合はエラーとする
		"""
		if views.KeyValueSettingDialogBase.KeySettingValidation(self.oldKeyConfig,self.values[1],self.log):
			event.Skip()
		return


class SettingDialog(views.KeyValueSettingDialogBase.SettingDialogBase):
	"""設定内容を入力するダイアログ"""

	def __init__(self,parent,name="",path="",key=""):
		super().__init__(
				parent,
				((_("登録名"),True),(_("場所"),True),(_("ショートカット"),False)),
				(None,(_("参照"),self.getRef),(_("設定"),self.SetKey)),
				name,path,key
				)

	def Initialize(self):
		return super().Initialize(_("登録内容の入力"))

	def getRef(self,event):
		d=wx.DirDialog(self.wnd,"場所の選択",style=wx.DD_DIR_MUST_EXIST | wx.DD_SHOW_HIDDEN)
		if d.Show()==wx.ID_CANCEL:
			return
		self.edits[1].SetValue(d.GetPath())

	def Validation(self,event):
		if self.edits[0].GetLineText(0)=="" or self.edits[1].GetLineText(0)=="":
			return
		path=os.path.expandvars(self.edits[1].GetLineText(0))
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
			self.edits[2].SetValue("")
			globalVars.app.say(_("解除しました。"))
			return

		self.edits[2].SetValue(d.GetValue())
		globalVars.app.say(_("%s に設定しました。") % (d.GetValue()))
		return
