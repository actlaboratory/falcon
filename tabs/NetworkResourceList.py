# -*- coding: utf-8 -*-
#Falcon network resource List tab
#Copyright (C)2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
ネットワークリソースリストです。ファイル操作関連は一切できません。
"""

import wx
import browsableObjects
import globalVars
import fileOperator
import misc

from simpleDialog import *
from . import base

class NetworkResourceListTab(base.FalconTabBase):
	"""ネットワークリソースリストが表示されているタブ。"""

	blockMenuList=[
		"FILE_RENAME",
		"FILE_CHANGEATTRIBUTE",
		"FILE_TRASH",
		"FILE_DELETE",
		"FILE_MKDIR",
		"EDIT_CUT",
		"EDIT_PAST",
		"EDIT_SEARCH",
		"MOVE_FORWARD_STREAM",
		"MOVE_TOPFILE",
		"MOVE_OPEN_HERE_",
		"TOOL_DIRCALC",
		"TOOL_HASHCALC",
		"TOOL_ADDPATH",
		"TOOL_EXEC_PROGRAM",
		"TOOL_EJECT_DRIVE",
		"TOOL_EJECT_DEVICE",
		"READ_CONTENT_PREVIEW",
		"READ_CONTENT_READHEADER",
		"READ_CONTENT_READFOOTER",
	]

	#end Update

	def GoBackward(self):
		"""ドライブ一覧へ戻る"""
		target=""
		cursorTarget=self.listObject.rootDirectory[0]
		return self.Move(target,cursorTarget)

	def OnLabelEditEnd(self,event):
		evt.Veto()
		return

	def ReadCurrentFolder(self):
		globalVars.app.say(_("現在は、"+self.listObject.rootDirectory), interrupt=True)

	def ReadListItemNumber(self,short=False):
		#shortもlongも関係ない
		globalVars.app.say(_("項目数 %(count)d") % {'count': len(self.listObject)})

	def ReadListInfo(self):
		globalVars.app.say(_("ネットワークリソースの一覧を一覧中、 %(max)d個中 %(current)d個目") %{'max': len(self.listObject), 'current': self.GetFocusedItem()+1}, interrupt=True)

	def GetTabName(self):
		"""タブコントロールに表示する名前"""
		return self.listObject.rootDirectory

	def GetRootObject(self):
		"""ドライブ詳細情報表示で用いる"""
		obj=browsableObjects.NetworkResource()
		obj.Initialize(self.listObject.rootDirectory[2:],self.listObject.rootDirectory,"")
		return obj
