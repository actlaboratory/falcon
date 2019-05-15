# -*- coding: utf-8 -*-
#Falcon wx test view
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import gettext
import logging
import os
import sys
import wx
from logging import getLogger, FileHandler, Formatter

from .base import *
import constants
import DefaultSettings
import errorCodes
import globalVars
import keymap
import misc
from simpleDialog import *
import views.ViewCreator

class View(BaseView):
	def Initialize(self):
		t=misc.Timer()
		self.identifier="wxTestView"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		self.app=globalVars.app
		super().Initialize("wxテスト",self.app.config.getint(self.identifier,"sizeX"),self.app.config.getint(self.identifier,"sizeY"))
		self.InstallControls()
		self.hFrame.Show()
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallControls(self):
		"""いろんなwidgetを設置する。"""
		self.creator=views.ViewCreator.ViewCreator(1,self.hFrame)
#		self.hPanel=wx.Panel(self.hFrame, wx.ID_ANY)
#		self.hPanel.SetBackgroundColour("#0000ff")		#項目のない部分の背景色
#		self.hPanel.SetAutoLayout(True)
		#その1　ボタン
		self.hButton=self.creator.button("何かする",self.OnButton)
#		self.hButton=wx.Button(self.hPanel, wx.ID_ANY, '何かする')
#		self.hButton.Bind(wx.EVT_BUTTON, self.OnButton)
		#その2　チェックボックス
		self.hCheckBox=self.creator.checkbox("何かを切り替える",self.OnCheckBox)
#		self.hCheckBox=wx.CheckBox(self.hPanel, wx.ID_ANY, "何かを切り替える")
#		self.hCheckBox.Bind(wx.EVT_CHECKBOX, self.OnCheckBox)

		#その3　ラジオボタン
		radioitems=["猫","犬","サル"]
		self.hRadioBox=self.creator.radiobox("何かを選ぶ",radioitems,self.OnRadioBox)
#		self.hRadioBox=wx.RadioBox(self.hPanel, label='何かを選ぶ', choices=radioitems)
#		self.hRadioBox.Bind(wx.EVT_RADIOBOX,self.OnRadioBox)

		#その4　入力ボックス
		self.hStaticText,self.hTextCtrl=self.creator.inputbox("何か書く")
#		self.hStaticText=wx.StaticText(self.hPanel, -1, "入力")
#		self.hTextCtrl=wx.TextCtrl(self.hPanel, -1)
		#ここまで

		self.sizer=wx.BoxSizer(wx.HORIZONTAL)
		self.sizer.Add(self.hButton)
		self.sizer.Add(self.hCheckBox)
		self.sizer.Add(self.hRadioBox)
		self.sizer.Add(self.hStaticText)
		self.sizer.Add(self.hTextCtrl)
		self.creator.getPanel().SetSizer(self.sizer)

	def OnButton(self,evt):
		dialog("Button pressed","Input box content: %s" % self.hTextCtrl.GetValue())

	def OnCheckBox(self,evt):
		dialog("Checkbox changed","Checked=%s" % self.hCheckBox.GetValue())

	def OnRadioBox(self,evt):
		obj=evt.GetEventObject()
		dialog("radiobutton changed","Selected: %s" % obj.GetStringSelection())

