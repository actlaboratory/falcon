# -*- coding: utf-8 -*-
#Falcon grep result tab
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
grep検索の結果が格納されます。同じファイルで複数のヒットがあった場合、エントリの数が増えていきます。
"""

import os
import gettext
import logging
import wx
import errorCodes
import lists
import browsableObjects
import globalVars
import fileOperator
import misc
import workerThreads
import workerThreadTasks
import StringUtil

from win32com.shell import shell, shellcon
from . import fileList

class GrepResultTab(fileList.FileListTab):
	"""grepの検索結果が表示されているタブ。"""

	blockMenuList=[
		"FILE_CHANGEATTRIBUTE",
		"EDIT_PAST",
		"EDIT_SEARCH",
		"MOVE_FORWARD_TAB",
		"MOVE_TOPFILE",
		"MOVE_BACKWARD",
		"TOOL_ADDPATH",
		"TOOL_EJECT_DRIVE",
		"TOOL_EJECT_DEVICE",
		"TOOL_EXEC_PROGRAM"
	]

	def StartSearch(self,rootPath,searches,keyword, isRegularExpression):
		self.listObject=lists.GrepResultList()
		self.listObject.Initialize(rootPath,searches,keyword, isRegularExpression)
		self.SetListColumns(self.listObject)
		workerThreads.RegisterTask(workerThreadTasks.PerformSearch,{'listObject': self.listObject, 'tabObject': self})

		#タブの名前変更を通知
		globalVars.app.hMainView.UpdateTabName()

	def _onSearchHitCallback(self,hits):
		"""コールバックで、ヒットしたオブジェクトのリストが降ってくるので、それをリストビューに追加していく。"""
		globalVars.app.PlaySound("click.ogg")
		for elem in hits:
			self.hListCtrl.Append(elem.GetListTuple())

	def GoBackward(self):
		return errorCodes.BOUNDARY

	def GoForward(self,stream,admin=False):
		"""検索結果表示では、フォルダを開くときに別タブを生成する。"""
		index=self.GetFocusedItem()
		elem=self.listObject.GetElement(index)
		if (not stream) and (type(elem)==browsableObjects.File or type(elem)==browsableObjects.GrepItem) :#このファイルを開く
			misc.RunFile(elem.fullpath,admin)
			return
		else:
			#新しいタブで開く
			globalVars.app.hMainView.Navigate(elem.fullpath,as_new_tab=True)
		#end ファイルを開くか移動するか
	#end GoForward

	def ReadCurrentFolder(self):
		state=_("grep検索完了") if self.listObject.GetFinishedStatus() is True else _("grep検索中")
		globalVars.app.say(_("キーワード %(keyword)s で ディレクトリ %(dir)s を%(state)s") % {'keyword': self.listObject.GetKeywordString(), 'dir': self.listObject.rootDirectory, 'state': state}, interrupt=True)

	def ReadListItemNumber(self,short=False):
		globalVars.app.say(_("検索結果 %(results)d件") % {'results': len(self.listObject)}, interrupt=True)

	def ReadListInfo(self):
		globalVars.app.say(_("%(keyword)sのgrep検索結果を %(sortkind)sの%(sortad)sで一覧中、 %(max)d個中 %(current)d個目") %{'keyword': self.listObject.GetKeywordString(), 'sortkind': self.listObject.GetSortKindString(), 'sortad': self.listObject.GetSortAdString(), 'max': len(self.listObject), 'current': self.GetFocusedItem()+1}, interrupt=True)

	def UpdateFilelist(self,silence=False,cursorTargetName=""):
		"""検索をやり直す。ファイルは非同期処理で増えるので、cursorTargetNameは使用されない。"""
		if not self.listObject.GetFinishedStatus():
			globalVars.app.say(_("現在検索中です。再建策はできません。"), interrupt=True)
			return
		#end まだ検索終わってない
		if silence==False:
			globalVars.app.say(_("再建策"), interrupt=True)
		#end not silence
		self.hListCtrl.DeleteAllItems()
		self.listObject.RedoSearch()
		workerThreads.RegisterTask(workerThreadTasks.PerformSearch,{'listObject': self.listObject, 'tabObject': self})

	def GetTabName(self):
		"""タブコントロールに表示する名前"""
		word=self.listObject.GetKeywordString()
		word=StringUtil.GetLimitedString(word,globalVars.app.config["view"]["header_title_length"])
		return _("%(word)sの検索") % {"word":word}

