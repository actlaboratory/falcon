# -*- coding: utf-8 -*-
#Falcon key config view
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx

import globalVars
import keymap
import misc
import views.ViewCreator

from logging import getLogger
from views.baseDialog import *

TIMER_INTERVAL=100

class Dialog(BaseDialog):
	def __init__(self,parent,filter=None,keyEntries=None,keyAddSet=None,keyDeleteSet=None):
		super().__init__()
		self.parent=parent				#親ウィンドウ
		self.filter=filter				#キーフィルタ
		if self.filter==None:			#キーフィルタ未指定ならデフォルトとしてメインビューで設定されたキーフィルタを適用
			self.filter=globalVars.app.hMainView.menu.keymap.filter
		self.keyEntries=keyEntries		#既存のkeymap.AcceleratorEntry(重複設定防止に利用)
		self.keyAddSet=keyAddSet		#未確定の編集で追加中のキーセット(重複設定防止に利用)	(例：Set("CTRL","ALT","A")
		self.keyDeleteSet=keyDeleteSet	#未確定の編集で削除中のキーセット(重複設定防止に利用)	(例：Set("CTRL","ALT","A")

		self.result=""					#取得した入力キー(結果格納・外部参照用)
		self.key=""						#取得した入力キー(内部処理用)
		self.timer=None					#wx.Timerオブジェクト

	def Initialize(self):
		t=misc.Timer()
		self.identifier="keyConfigDialog"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		super().Initialize(self.parent,_("キー設定"))
		self.wnd.Bind(wx.EVT_TIMER, self.OnTimer)
		self.InstallControls()
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""
		self.mainArea=views.ViewCreator.BoxSizer(self.sizer,wx.HORIZONTAL,wx.ALIGN_CENTER)

		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.mainArea,wx.VERTICAL,20)
		self.creator.staticText(_("設定したいキーの組み合わせを押してください..."))
		self.keyNameText=self.creator.staticText("")
		self.errorText=self.creator.staticText("")


		self.buttonArea=views.ViewCreator.BoxSizer(self.sizer,wx.HORIZONTAL, wx.ALIGN_RIGHT)
		self.creator=views.ViewCreator.ViewCreator(1,self.panel,self.buttonArea,wx.HORIZONTAL,20)
		self.bCancel=self.creator.cancelbutton(_("キャンセル"),None)

	def Show(self):
		self.panel.Layout()
		self.sizer.Fit(self.wnd)
		self.wnd.Centre()
		self.timer=wx.Timer(self.wnd)
		self.timer.Start(TIMER_INTERVAL)
		result=self.wnd.ShowModal()
		if result!=wx.ID_CANCEL:
			self.value=self.GetData()
		self.Destroy()
		return result


	def GetData(self):
		return self.result

	def OnTimer(self,event):
		self.timer.Stop()

		#キーの判定
		hits=[]
		for name in self.filter.GetUsableKeys():
			#マウス関連は利用不可
			code=keymap.str2key[name]
			if code<=4:
				continue
			#カテゴリキーは取得不可、NumLockとCapsLockは押し下げ状態ではなく現在のON/OFFを返してしまうので
			if type(code)==wx.KeyCategoryFlags or name=="NUMLOCK" or name=="SCROLL":
				continue
			if wx.GetKeyState(code):
				hits.append(name)

		if hits:
			self.key=""
			for i,key in enumerate(hits):
				self.key+=key
				if i<len(hits)-1:
					self.key+="+"
			if len(self.result)<len(self.key):
				self.result=self.key
			self.keyNameText.SetLabel(self.result)
		else:									#キーが放されたら前の入力を検証する
			if self.result!="":
				if self.filter.Check(self.result):
					if self.IsDuplicated(self.result):
						tmp=_("このパターンは既に登録済みです。")
						self.errorText.SetLabel(tmp)
						globalVars.app.say(tmp,True)
					else:
						self.wnd.EndModal(wx.ID_OK)		#正しい入力なのでダイアログを閉じる
						return
				else:
					self.errorText.SetLabel(self.filter.GetLastError())
					globalVars.app.say(self.filter.GetLastError(),True)

				self.key=""
				self.result=""
		self.timer.Start(TIMER_INTERVAL)
		return

	def IsDuplicated(self,v):
		"""キーパターンvが既存のものと重複するか否かを判定する"""
		e=keymap.makeEntry("DUMMY",v,self.filter,self.log)
		if e==False:
			self.log.worning("makeEntry(%s) returned False." % v)
			return True
		s=set(v.split("+"))
		if e in self.keyEntries and (self.keyDeleteSet==None or s not in self.keyDeleteSet):
			return True
		elif self.keyAddSet!=None and s in self.keyAddSet:
			return True
		return False
