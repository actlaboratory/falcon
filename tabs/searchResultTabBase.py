# -*- coding: utf-8 -*-
#Falcon searchResultTabBase
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
	通常検索・ファイル内容検索共通の関数群
"""

import browsableObjects
import errorCodes
import globalVars
import misc
import StringUtil
import tabs
import workerThreads
import workerThreadTasks

class SearchResultTabBase(tabs.fileList.FileListTab):

	blockMenuList=[
		"FILE_MKDIR",
		"EDIT_PAST",
		"EDIT_SEARCH",
		"MOVE_BACKWARD",
		"MOVE_MARKSET",
		"MOVE_MARK",
		"TOOL_ADDPATH",
		"TOOL_EJECT_DRIVE",
		"TOOL_EJECT_DEVICE",
		"TOOL_EXEC_PROGRAM"
	]

	def StartSearch(self,rootPath,searches,keyword, isRegularExpression):
		self.listObject=self.listType()
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
		#end 追加
		if self.listObject.GetFinishedStatus():
			self.listObject.ApplySort()
			self.hListCtrl.DeleteAllItems()
			self.UpdateListContent(self.listObject.GetItems())

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

	def GoForward(self,stream,admin=False):
		"""検索結果表示では、フォルダを開くときに別タブを生成する。"""
		index=self.GetFocusedItem()
		elem=self.listObject.GetElement(index)
		if (not stream) and (not isinstance(elem,browsableObjects.Folder)): #このファイルを開く
			misc.RunFile(elem.fullpath,admin)
			return
		else:
			#新しいタブで開く
			globalVars.app.hMainView.Navigate(elem.fullpath,as_new_tab=True)
		#end ファイルを開くか移動するか
	#end GoForward

	def GoBackward(self):
		return errorCodes.BOUNDARY

	def ReadCurrentFolder(self):
		state=_("検索完了") if self.listObject.GetFinishedStatus() is True else _("検索中")
		globalVars.app.say(_("キーワード %(keyword)s で ディレクトリ %(dir)s を%(state)s") % {'keyword': self.listObject.GetKeywordString(), 'dir': self.listObject.rootDirectory, 'state': state}, interrupt=True)

	def ReadListItemNumber(self,short=False):
		globalVars.app.say(_("検索結果 %(results)d件") % {'results': len(self.listObject)}, interrupt=True)

	def GetTabName(self):
		"""タブコントロールに表示する名前"""
		word=self.listObject.GetKeywordString()
		word=StringUtil.GetLimitedString(word,globalVars.app.config["view"]["header_title_length"])
		word=_("%(word)sの検索") % {"word":word}
		return word
