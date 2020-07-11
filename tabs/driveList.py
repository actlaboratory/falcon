# -*- coding: utf-8 -*-
#Falcon Drive List tab
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
ドライブリストです。ファイルリストと比べると、機能が制限されます。
"""

import os
import wx

import browsableObjects
import errorCodes
import globalVars
import fileOperator
import fileSystemManager
import misc
import workerThreads
import workerThreadTasks

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
		"EDIT_PAST",
		"EDIT_SEARCH",
		"MOVE_BACKWARD",
		"MOVE_TOPFILE",
		"MOVE_OPEN_HERE_",
		"TOOL_DIRCALC",
		"TOOL_HASHCALC",
		"TOOL_ADDPATH",
		"TOOL_EXEC_PROGRAM",
		"READ_CONTENT_PREVIEW",
		"READ_CONTENT_READHEADER",
		"READ_CONTENT_READFOOTER",
	]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.selectItemMenuConditions[2].extend([
			"EDIT_OPENCONTEXTMENU"
		])
		self.networkListTask=None
		self._getNetworkList()

	def _getNetworkList(self):
		if self.networkListTask is not None:
			self.networkListTask.Cancel()
			self.networkListTask=None
		#end cancel previous
		self.networkListTask=workerThreads.RegisterTask(workerThreadTasks.GetNetworkResources, {"onAppend": self.OnAppendNetworkResource, "onFinish": self.OnFinishNetworkResource})

	def OnAppendNetworkResource(self,resource):
		self.listObject.AppendNetworkResource(resource)
		self._AppendElement(resource)

	def OnFinishNetworkResource(self,number):
		if number==-1:
			dialog(_("エラー"), _("ネットワークリソース一覧が取得できませんでした。"))
		#end error
		globalVars.app.say(_("ネットワークドライブ数: %d" % number))
		self.networkTask=None

	def GoBackward(self):
		"""内包しているフォルダ/ドライブ一覧へ移動する。"""
		return errorCodes.BOUNDARY

	def OnLabelEditEnd(self,evt):
		self.isRenaming=False
		self.parent.SetShortcutEnabled(True)
		if evt.IsEditCancelled():		#ユーザによる編集キャンセル
			return
		e=self.hListCtrl.GetEditControl()
		f=self.listObject.GetElement(self.GetFocusedItem())
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

	def ReadCurrentFolder(self):
		globalVars.app.say(_("現在は、ドライブ洗濯"), interrupt=True)

	def ReadListItemNumber(self,short=False):
		if short:
			globalVars.app.say(_("ドライブ数 %(drives)d") % {'drives': len(self.listObject)})
		else:
			globalVars.app.say(_("ドライブ %(drives)d個") % {'drives': len(self.listObject)}, interrupt=True)

	def ReadListInfo(self):
		globalVars.app.say(_("ドライブ一覧を %(sortkind)sの%(sortad)sで一覧中、 %(max)d個中 %(current)d個目") %{'sortkind': self.listObject.GetSortKindString(), 'sortad': self.listObject.GetSortAdString(), 'max': len(self.listObject), 'current': self.GetFocusedItem()+1}, interrupt=True)

	def GetTabName(self):
		"""タブコントロールに表示する名前"""
		return _("ドライブ一覧")

	def OpenContextMenu(self,event):
		menu=wx.Menu()
		if type(self.GetFocusedElement())==browsableObjects.Drive:
			globalVars.app.hMainView.menu.RegisterMenuCommand(menu,{
				"TOOL_EJECT_DRIVE":_("ドライブの取り外し"),
				"TOOL_EJECT_DEVICE":_("デバイスの取り外し"),
			})
		globalVars.app.hMainView.menu.RegisterMenuCommand(menu,{
			"VIEW_DRIVE_INFO":_("ドライブ情報の表示"),
			"FILE_SHOWPROPERTIES":_("プロパティを表示")
		})
		globalVars.app.hMainView.PopupMenu(menu)

	def GetRootObject(self):
		"""ドライブ詳細情報表示で用いる"""
		return self.GetFocusedElement()

	def OnNetworkListRetrieved(self,elem):
		self._AppendElement(elem)

	def OnClose(self):
		"""ネットワークリソース一覧をキャンセルして大気"""
		if self.networkListTask: self.networkListTask.Cancel()