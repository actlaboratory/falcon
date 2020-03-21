# -*- coding: utf-8 -*-
#Falcon Drive List tab
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
ドライブリストです。ファイルリストと比べると、機能が制限されます。
"""

import os
import gettext
import wx
import errorCodes
import lists
import browsableObjects
import globalVars
import fileOperator
import misc
import workerThreads
import workerThreadTasks
import fileSystemManager
import tabs.fileList

from simpleDialog import *
from win32com.shell import shell, shellcon
from . import base

class DriveListTab(base.FalconTabBase):
	"""ドライブリストが表示されているタブ。"""

	blockMenuList=[
		"FILE_CHANGEATTRIBUTE",
		"FILE_TRASH",
		"FILE_DELETE",
		"FILE_MKDIR",
		"EDIT_CUT",
		"EDIT_SEARCH",
		"MOVE_BACKWARD",
		"MOVE_TOPFILE",
		"TOOL_DIRCALC",
		"TOOL_HASHCALC",
		"TOOL_ADDPATH"
	]

	def Update(self,cursor=""):
		"""指定された要素をタブに適用する。"""
		self._cancelBackgroundTasks()
		lst=lists.DriveList()
		lst.Initialize(None)
		self.hListCtrl.DeleteAllItems()
		self.SetListColumns(lst)
		self.listObject=lst
		self.UpdateListContent(self.listObject.GetItems())
		if cursor!="":
			c=lst.Search(cursor,1)
			self.hListCtrl.Select(c)
			self.hListCtrl.Focus(c)
		#end カーソル初期位置を設定
	#end Update

	def GoBackward(self):
		"""内包しているフォルダ/ドライブ一覧へ移動する。"""
		return errorCodes.BOUNDARY

	def OnLabelEditEnd(self,evt):
		self.isRenaming=False
		self.parent.SetShortcutEnabled(True)
		if evt.IsEditCancelled():		#ユーザによる編集キャンセル
			return
		e=self.hListCtrl.GetEditControl()
		f=self.listObject.GetElement(self.hListCtrl.GetFocusedItem())
		newName=e.GetLineText(0)
		error=fileSystemManager.ValidationObjectName(newName,fileSystemManager.pathTypes.VOLUME_LABEL)
		if error:
			dialog(_("エラー"),error)
			evt.Veto()
			return
		inst={"operation": "rename", "files": [f.fullpath], "to": [newName]}
		op=fileOperator.FileOperator(inst)
		ret=op.Execute()
		if op.CheckSucceeded()==0:
			dialog(_("エラー"),_("名前が変更できません。"))
			evt.Veto()
			return
		#end fail
		f.basename=e.GetLineText(0)
	#end onLabelEditEnd

	def MakeShortcut(self,option):
		prm=""
		dir=""
		if option["type"]=="shortcut":
			prm=option["parameter"]
			dir=option["directory"]
		target=self.parent.activeTab.GetSelectedItems().GetElement(0).fullpath
		dest=option["destination"]
		if not os.path.isabs(dest):	#早退の場合は絶対に直す
			dest=os.path.normpath(os.path.join(os.path.dirname(target),dest))

		#TODO:
		#相対パスでの作成に後日対応する必要がある
		#ハードリンクはドライブをまたげないのでバリデーションする
		#ファイルシステムを確認し、対応してない種類のものは作れないようにバリデーションする
		#作業フォルダの指定に対応する(ファイルオペレータ側の修正も必用)

		if option["type"]=="shortcut":
			inst={"operation":option["type"], "target": [(dest,target,prm)]}
		else:
			inst={"operation":option["type"], "from": [target], "to": [dest]}
		#end ショートカットかそれ以外
		op=fileOperator.FileOperator(inst)
		ret=op.Execute()
		if op.CheckSucceeded()==0:
			dialog(_("エラー"),_("ショートカットの作成に失敗しました。"))
			return
		#end error
		self.UpdateFilelist(silence=True)

	def FileOperationTest(self):
		if self.task:
			self.task.Cancel()
		else:
			self.task=workerThreads.RegisterTask(workerThreadTasks.DebugBeep)

	def ShowProperties(self):
		index=self.GetFocusedItem()
		shell.ShellExecuteEx(shellcon.SEE_MASK_INVOKEIDLIST,0,"properties",self.listObject.GetElement(index).fullpath)
