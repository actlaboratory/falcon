# -*- coding: utf-8 -*-
#Falcon past progress tab
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
コピー/貼り付けの進捗状況を表示するタブ。
"""

import os
import wx

import browsableObjects
import errorCodes
import globalVars
import misc
import StringUtil
import tabs
import simpleDialog

from . import base

class PastProgressTab(base.FalconTabBase):
	def Initialize(self,parent,creator,existing_listctrl=None):
		super().Initialize(parent,creator,existing_listctrl)
	blockMenuList=[
		"FILE_RENAME",
		"FILE_CHANGEATTRIBUTE",
		"FILE_MAKESHORTCUT",
		"FILE_TRASH",
		"FILE_DELETE",
		"FILE_MKDIR",
		"EDIT_COPY",
		"EDIT_CUT",
		"EDIT_PAST",
		"EDIT_SEARCH",
		"EDIT_UPDATEFILELIST",
		"MOVE_FORWARD",
		"MOVE_FORWARD_ADMIN",
		"MOVE_EXEC_ORIGINAL_ASSOCIATION",
		"MOVE_FORWARD_TAB",
		"MOVE_FORWARD_STREAM",
		"MOVE_BACKWARD",
		"MOVE_TOPFILE",
		"MOVE_HIST_NEXT",
		"MOVE_HIST_PREV",
		"MOVE_MARKSET",
		"MOVE_MARK",
		"READ_CONTENT_PREVIEW",
		"READ_CONTENT_READHEADER",
		"READ_CONTENT_READFOOTER",
		"TOOL_DIRCALC",
		"TOOL_HASHCALC",
		"TOOL_ADDPATH",
		"TOOL_EJECT_DRIVE",
		"TOOL_EJECT_DEVICE",
		"VIEW_DRIVE_INFO",
	]

	def SetFileOperator(self,operator):
		"""ファイルオペレーターを設定して、オペレーション終了時のコールバックを登録する。"""
		self.fileOperator=operator
		operator.SetCallback("finished",self.OnOperationFinish)
		operator.SetCallback("setPercentage",self.OnPercentageSet)
		operator.SetCallback("confirm",self.OnConfirm)

	def OnOperationFinish(self,op,parameters):
		if self.listObject.GetUnresolvedCount()==0: globalVars.app.hMainView.CloseTab(self)

	def OnPercentageSet(self,op,parameters):
		self.listObject.SetHeaderPercentage(op.GetPercentage())
		self._replaceElement(self.listObject.GetHeaderObject(),0)

	def OnConfirm(self,op,parameters):
		path=parameters["elem"].path
		elem=browsableObjects.PastProgressItem()
		elem.Initialize(os.path.basename(path),path,_("確認"),_("宛先に同名ファイルが存在します"))
		self.listObject.Append(elem)
		self._AppendElement(elem)

	def OpenContextMenu(self,event):
		simpleDialog.dialog("コンテキストメニュー検討中","コンテキストメニューで、問い合わせへの応答などできるようにしたいと思ってます。")

	def ReadCurrentFolder(self):
		globalVars.app.say("貼り付けの結果を閲覧中")

	def ReadListItemNumber(self,short=False):
		globalVars.app.say(_("項目数 %(results)d件") % {'results': len(self.listObject)}, interrupt=True)

	def GetTabName(self):
		"""タブコントロールに表示する名前"""
		word="ほにゃぺけからほにゃぺけへの貼り付け"
		word=StringUtil.GetLimitedString(word,globalVars.app.config["view"]["header_title_length"])
		return word

	def DeleteAllItems(self):
		super().DeleteAllItems()

	def OnClose(self):
		super().OnClose()
		if self.fileOperator.GetFinishedState is False:
			simpleDialog.dialog("ファイル処理中","ファイル操作を実行中のため、このタブを閉じることはできません。")

	def OnLabelEditStart(self,evt):
		pass

	def OnLabelEditEnd(self,evt):
		pass

