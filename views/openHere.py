# -*- coding: utf-8 -*-
#Falcon openHere command Setting view
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import copy
import os
import wx

import globalVars
import misc

import views.keyConfig
import views.KeyValueSettingDialogBase

from simpleDialog import dialog

class Dialog(views.KeyValueSettingDialogBase.KeyValueSettingDialogBase):

	def __init__(self,config,keyConfig):
		info=[
			(_("名前"),wx.LIST_FORMAT_LEFT,200),
			(_("実行ファイル名"),wx.LIST_FORMAT_LEFT,350),
			(_("ショートカット"),wx.LIST_FORMAT_LEFT,200)
		]
		super().__init__("openHereSettingDialog",SettingDialog,info,config,keyConfig)
		self.oldKeyConfig=copy.copy(keyConfig)


	def Initialize(self):
		return super().Initialize(self.app.hMainView.hFrame,_("「ここで開く」コマンドの設定"))

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
				((_("名前"),True),(_("実行ファイル名(引数指定可)"),True),(_("ショートカット"),False)),
				(None,(_("参照"),self.getRef),(_("設定"),self.SetKey)),
				name,path,key
				)

	def Initialize(self):
		return super().Initialize(_("登録内容の入力"))

	def getRef(self,event):
		pathext=os.getenv("pathext").replace(";",";*")
		d=wx.FileDialog(self.wnd,"実行ファイルの選択",wildcard="実行ファイル("+pathext+")",style=wx.FD_FILE_MUST_EXIST | wx.FD_SHOW_HIDDEN)
		if d.ShowModal()==wx.ID_CANCEL:
			return
		self.edits[1].SetValue(d.GetPath())

	def Validation(self,event):
		if self.edits[0].GetLineText(0)=="" or self.edits[1].GetLineText(0)=="":
			return
		path,prm=misc.PathParamSplit(self.edits[1].GetLineText(0))
		path=os.path.expandvars(path)
		if path==None:
			dialog(_("エラー"),_("指定された実行ファイルの書式が正しくありません。"))
			return
		if not os.path.isabs(path):
			dialog(_("エラー"),_("実行ファイルのパスは絶対パスで指定してください。"))
			return
		if not os.path.isfile(path):
			dialog(_("エラー"),_("入力された実行ファイルが存在しません。パスを確認してください。"))
			return
		if not misc.GetExecutableState(path):
			dialog(_("エラー"),_("指定されたファイルは存在しますが、実行可能な形式のファイルではありません。"))
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
