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
import views.OperationSelecter
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
		print("setFileOperator")
		self.fileOperator=operator
		operator.SetCallback("finished",self.OnOperationFinish)
		operator.SetCallback("setPercentage",self.OnPercentageSet)
		operator.SetCallback("confirm",self.OnConfirm)
		# パーセンテージのコールバックが来るのは、次にパーセンテージが変化するときだけである。なので、現時点でのパーセンテージは、このタイミングで手動で得ておく。
		self.OnPercentageSet(operator,{})
		# 確認項目を最新にしておく
		self.listObject.Update(operator.GetConfirmationManager())
		self.Update(self.listObject)

	def OnOperationFinish(self,op,parameters):
		if self.listObject.GetUnresolvedCount()==0: globalVars.app.hMainView.CloseTab(self)

	def OnPercentageSet(self,op,parameters):
		self.listObject.SetHeaderPercentage(op.GetPercentage())
		self._replaceElement(self.listObject.GetHeaderObject(),0)

	def OnConfirm(self,op,parameters):
		print("confirm captured")
		path=parameters.GetElement().path
		elem=browsableObjects.PastProgressItem()
		elem.Initialize(os.path.basename(path),path,_("確認"),parameters.GetMessageString())
		self.listObject.Append(elem)
		print("called append")
		self._AppendElement(elem)

	def OpenContextMenu(self,event):
		m=wx.Menu()
		m.Append(0,"詳細を表示")
		item=self.hListCtrl.GetPopupMenuSelectionFromUser(m)
		m.Destroy()
		print(item)
		elem=self.GetFocusedElement()
		index=elem.GetConfirmationManagerIndex()
		confs=self.fileOperator.GetConfirmationManager()
		confirmElem=confs.GetAt(index)
		e=confirmElem.GetElement()
		from_path=e.path
		dest_path=e.destpath
		print(dest_path)
		from_stat=os.stat(from_path)
		dest_stat=os.stat(dest_path)
		info=[
			(_("名前"),"test.txt","",""),
			(_("サイズ"),misc.ConvertBytesTo(dest_stat.st_size,misc.UNIT_AUTO,True),"→",misc.ConvertBytesTo(from_stat.st_size,misc.UNIT_AUTO,True)),
			(_("更新日時"),datetime.datetime.fromtimestamp(dest_stat.st_mtime),"→",datetime.datetime.fromtimestamp(from_stat.st_mtime))
		]
		d=views.OperationSelecter.Dialog(_("上書きしますか？"),info,views.OperationSelecter.GetMethod("ALREADY_EXISTS"),False)
		d.Initialize()
		d.Show()
		val=d.GetValue()
		if val['all'] is True:#「以降も同様に処理」がオン
			confs.RespondAll(confirmElem,val['response'])
		else:#この1件だけ
			confirmElem.SetResponse(d.GetValue())#渓谷に対して、文字列でレスポンスする
		#end これ以降全てかこれだけか
		self.fileOperator.UpdateConfirmation()#これで繁栄する
		self.fileOperator.Execute()#これでコピーを再実行

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

