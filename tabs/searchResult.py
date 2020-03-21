# -*- coding: utf-8 -*-
#Falcon search result tab
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
検索結果が格納されていきます。一通りのファイル操作を行うことができます。
"""

import os
import gettext
import logging
import wx
import clipboard
import errorCodes
import lists
import browsableObjects
import globalVars
import fileOperator
import misc
import workerThreads
import workerThreadTasks

from win32com.shell import shell, shellcon
from . import fileList

class SearchResultTab(fileList.FileListTab):
	"""検索結果が表示されているタブ。"""
	def StartSearch(self,rootPath,searches,keyword):
		self.listObject=lists.SearchResultList()
		self.listObject.Initialize(rootPath,searches,keyword)
		self.SetListColumns(self.listObject)
		workerThreads.RegisterTask(workerThreadTasks.PerformSearch,{'listObject': self.listObject, 'tabObject': self})

	def _onSearchHitCallback(self,hits):
		"""コールバックで、ヒットした browsableObject のリストが降ってくるので、それをリストビューに追加していく。"""
		globalVars.app.PlaySound("click.ogg")
		for elem in hits:
			t=elem.GetListTuple()
			self.hListCtrl.Append((t[0],t[1],elem.fullpath,t[2],t[3],t[4]))

	def Copy(self):
		if not self.IsItemSelected(): return
		globalVars.app.say(_("コピー"))
		c=clipboard.ClipboardFile()
		c.SetFileList(self.GetSelectedItems().GetItemPaths())
		c.SendToClipboard()

	def Cut(self):
		if not self.IsItemSelected(): return
		globalVars.app.say(_("切り取り"))
		c=clipboard.ClipboardFile()
		c.SetOperation(clipboard.MOVE)
		c.SetFileList(self.GetSelectedItems().GetItemPaths())
		c.SendToClipboard()

	def OnLabelEditEnd(self,evt):
		self.isRenaming=False
		self.parent.SetShortcutEnabled(True)
		if evt.IsEditCancelled():		#ユーザによる編集キャンセル
			return
		e=self.hListCtrl.GetEditControl()
		f=self.listObject.GetElement(self.hListCtrl.GetFocusedItem())
		if isinstance(f,browsableObjects.Folder):
			newName=f.directory+"\\"+e.GetLineText(0)
			error=fileSystemManager.ValidationObjectName(newName,fileSystemManager.pathTypes.DIRECTORY)
		elif isinstance(f,browsableObjects.File):
			newName=f.directory+"\\"+e.GetLineText(0)
			error=fileSystemManager.ValidationObjectName(newName,fileSystemManager.pathTypes.FILE)
		else:
			newName=e.GetLineText(0)
			error=fileSystemManager.ValidationObjectName(newName,fileSystemManager.pathTypes.VOLUME_LABEL)
		#end フォルダかファイルかドライブか
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
		if isinstance(f,browsableObjects.File):
			f.fullpath=f.directory+"\\"+f.basename
		if isinstance(f,browsableObjects.Stream):
			f.fullpath=f.file+f.basename
	#end onLabelEditEnd

	#TODO:GoToTopFile(self):
