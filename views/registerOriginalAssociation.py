# -*- coding: utf-8 -*-
#Falcon register originalAssociation view
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import os
import re

import misc
import views.KeyValueSettingDialogBase

from simpleDialog import dialog

class Dialog(views.KeyValueSettingDialogBase.KeyValueSettingDialogBase):

	def __init__(self,config):
		info=[
			(_("拡張子"),wx.LIST_FORMAT_LEFT,250),
			(_("実行ファイル名"),wx.LIST_FORMAT_LEFT,550)
		]
		super().__init__(SettingDialog,info,config)

	def Initialize(self):
		return super().Initialize(self.app.hMainView.hFrame,"registOriginalAssociationDialog",_("拡張子の独自関連付け"))

	def DeleteValidation(self,key):
		return not "<default_" in key

class SettingDialog(views.KeyValueSettingDialogBase.SettingDialogBase):
	"""Dialogの上に作られ、各拡張子と実行ファイルの関連付けを入力するダイアログ"""

	def __init__(self,parent,extention="",path=""):
		super().__init__(
				parent,
				((_("拡張子"),not "<default_" in extention),(_("実行ファイル名"),True)),
				(None,(_("参照"),self.getRef)),
				extention,path
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
		path=os.path.expandvars(self.edits[1].GetLineText(0))
		if not os.path.isabs(path):
			dialog(_("エラー"),_("実行ファイルのパスは絶対パスで指定してください。"))
			return
		if not os.path.isfile(path):
			dialog(_("エラー"),_("入力された実行ファイルが存在しません。パスを確認してください。"))
			return
		if not misc.GetExecutableState(path):
			dialog(_("エラー"),_("指定されたファイルは存在しますが、実行可能な形式のファイルではありません。"))
			return
		if self.edits[0].GetLineText(0)=="<default_file>" or self.edits[0].GetLineText(0)=="<default_dir>":
			event.Skip()
			return
		if not re.match("^[a-zA-Z0-9\\-$~]+$",self.edits[0].GetLineText(0)):
			dialog(_("エラー"),_("入力された拡張子に利用できない文字が含まれています。"))
			return
		event.Skip()
