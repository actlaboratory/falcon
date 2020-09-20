# -*- coding: utf-8 -*-
# language select dialog

import wx

import constants
import globalVars
import views.ViewCreator
from logging import getLogger
from views.baseDialog import *

class langDialog(BaseDialog):
	def __init__(self):
		#まだglobalVars.appが未精製の状態での軌道の可能性があるのであえて呼ばない
		#super().__init__()

		self.identifier="languageSelectDialog"
		self.log=getLogger("%s.%s" % (constants.LOG_PREFIX,self.identifier))
		self.value=None
		self.viewMode="white"

	def Initialize(self):
		self.log.debug("created")
		super().Initialize(None,"language settings",0)
		self.InstallControls()
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""
		self.creator=views.ViewCreator.ViewCreator(self.viewMode,self.panel,self.sizer,wx.VERTICAL,20)

		self.langSelect = self.creator.combobox("language:", constants.DISPLAY_LANGUAGE, None, state=0,sizerFlag=wx.ALIGN_CENTER_HORIZONTAL)
		self.ok = self.creator.okbutton("OK", None)

	def GetData(self):
		select = self.langSelect.GetSelection()
		return constants.SUPPORTING_LANGUAGE[select]
