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
import listObjects
import browsableObjects
import globalVars
import constants
import fileOperator
import misc
import workerThreads
import workerThreadTasks
import fileSystemManager

from simpleDialog import *
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
		self.environment["FileList_sorting"]=int(globalVars.app.config["FileList"]["sorting"])
		self.environment["FileList_descending"]=int(globalVars.app.config["FileList"]["descending"])
		self.environment["DriveList_sorting"]=int(globalVars.app.config["DriveList"]["sorting"])
		self.environment["DriveList_descending"]=int(globalVars.app.config["DriveList"]["descending"])
		self.background_tasks=[]

