# -*- coding: utf-8 -*-
#Falcon search result tab
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
検索結果が格納されていきます。一通りのファイル操作を行うことができます。
"""

import sys
import os
import views.ViewCreator
import gettext
import logging
import wx
import win32api
import clipboard
import clipboardHelper
import errorCodes
import lists
import browsableObjects
import globalVars
import constants
import fileOperator
import misc
import workerThreads
import workerThreadTasks

from win32com.shell import shell, shellcon
from . import mainList

class SearchResultTab(mainList.MainListTab):
	"""検索結果が表示されているタブ。"""
	def Initialize(self,parent,creator):
		"""タブを初期化する。親ウィンドウの上にリストビューを作るだけ。"""
		self.log=logging.getLogger("falcon.searchResultTab")
		self.log.debug("Created.")
		self.parent=parent
		self.InstallListCtrl(creator)
		self.environment["sorting"]=int(globalVars.app.config["SearchResultList"]["sorting"])
		self.environment["descending"]=int(globalVars.app.config["SearchResultList"]["descending"])
		self.background_tasks=[]

	def StartSearch(self,rootPath,searches,keyword):
		self.listObject=lists.SearchResult(rootPath,searches,keyword,self.environment["sorting"],self.environment["descending"])
		workerThreads.RegisterTask(workerThreadTasks.PerformSearch,{'listObject': self.listObject, 'tabObject': self})

	def _onSearchHitCallback(self,hits):
		"""コールバックで、ヒットした browsableObject のリストが降ってくるので、それをリストビューに追加していく。"""
		for elem in hits:
			t=elem.GetListTuple()
			self.hListCtrl.Append((t[0],t[1],elem.fullpath,t[2],t[3],t[4]))
