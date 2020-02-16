# -*- coding: utf-8 -*-
#Falcon FileHash view
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import globalVars
import misc
import views.ViewCreator
from logging import getLogger
from views.baseDialog import *

hashTypes=[
	'md5',
	'sha1',
	'sha224',
	'sha256',
	'sha384',
	'sha512',
	'sha3_224',
	'sha3_256',
	'sha3_384',
	'sha3_512',
	'blake2s',
	'blake2b'
]

class Dialog(BaseDialog):
	def __init__(self,fname):
		self.fileName=fname

	def Initialize(self):
		t=misc.Timer()
		self.identifier="FileHashDialog"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		self.app=globalVars.app
		super().Initialize(self.app.hMainView.hFrame,_("ファイルハッシュの計算"))
		self.InstallControls()
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""

		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.sizer,wx.VERTICAL,20)
		self.combo=self.creator.combobox(_("値の種類"),hashTypes,self.changeAlgo)
		self.calcButton=self.creator.button(_("計算"),self.calcStart,wx.ALIGN_RIGHT)
		self.calcButton.Enable(False)

		self.resultFeeld,self.static=self.creator.inputbox(_("結果"),400)

		self.buttonArea=views.ViewCreator.BoxSizer(self.sizer,wx.HORIZONTAL,wx.ALIGN_BOTTOM | wx.ALIGN_RIGHT)
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.buttonArea,wx.HORIZONTAL,20)
		self.bOk=self.creator.okbutton(_("閉じる"),None)

		self.sizer.Fit(self.wnd)


	def Show(self):
		result=self.wnd.ShowModal()
		self.Destroy()
		return result

	def Destroy(self):
		self.log.debug("destroy")
		self.wnd.Destroy()

	def GetValue(self):
		return None

	def calcStart(self,event):
		hash=misc.calcHash(self.fileName,self.combo.GetStringSelection())
		self.resultFeeld.SetValue(hash)

	def changeAlgo(self,event):
		self.calcButton.Enable(True)
