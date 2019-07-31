# -*- coding: utf-8 -*-
#View Creator
#Copyright (C) 2019 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
from . import fontManager

class ViewCreator():

	# mode=1で白黒反転。その他は白。
	def __init__(self,mode,parent):
		self.mode=mode
		if isinstance(parent,wx.Panel):
			self.hPanel=parent
		else:
			self.hPanel=makePanel(mode,parent)
		self.font=fontManager.FontManager()


	def button(self,text,event):
		hButton=wx.Button(self.hPanel, wx.ID_ANY,label=text, name=text)
		hButton.Bind(wx.EVT_BUTTON,event)
		self.SetFace(hButton)
		return hButton

	def okbutton(self,text,event):
		hButton=wx.Button(self.hPanel, wx.ID_OK,label=text, name=text)
		hButton.Bind(wx.EVT_BUTTON,event)
		self.SetFace(hButton)
		return hButton

	def cancelbutton(self,text,event):
		hButton=wx.Button(self.hPanel, wx.ID_CANCEL,label=text, name=text)
		hButton.Bind(wx.EVT_BUTTON,event)
		self.SetFace(hButton)
		return hButton

	def checkbox(self,text,event):
		hCheckBox=wx.CheckBox(self.hPanel,wx.ID_ANY, label=text, name=text)
		hCheckBox.Bind(wx.EVT_CHECKBOX,event)
		self.SetFace(hCheckBox)
		return hCheckBox

	def radiobox(self,text,items,event):
		hRadioBox=wx.RadioBox(self.hPanel,label=text, name=text, choices=items)
		hRadioBox.Bind(wx.EVT_RADIOBOX,event)
		self.SetFace(hRadioBox)
		return hRadioBox

	def ListCtrl(self,**settings):
		hListCtrl=wx.ListCtrl(self.hPanel,wx.ID_ANY,**settings)
		self.SetFace(hListCtrl)
		hListCtrl.SetTextColour("#ffffff")				#文字色
		return hListCtrl

	def inputbox(self,text):
		hStaticText=wx.StaticText(self.hPanel, -1, label="入力", name="入力")
		hTextCtrl=wx.TextCtrl(self.hPanel, -1)
		self.SetFace(hTextCtrl)
		return hStaticText,hTextCtrl

	def getPanel(self):
		return self.hPanel

	def SetFace(self,target):
		if self.mode==1:
			target.SetBackgroundColour("#000000")		#背景色＝黒
#			target.SetForegroundColour("#ffffff")		#文字色＝白
		else:
			target.SetBackgroundColour("#ffffff")		#背景色＝白
			#target.SetForegroundColour("#000000")		#文字色＝黒
		target.SetThemeEnabled(False)
		target.SetFont(self.font.GetFont())

# parentで指定されたフレームにパネルを設置する
# modeはViewCreator.__init__と同様
def makePanel(mode,parent):
	hPanel=wx.Panel(parent,wx.ID_ANY)
	if mode==1:
		hPanel.SetBackgroundColour("#000000")		#項目のない部分の背景色＝黒
	else:
		hPanel.SetBackgroundColour("#ffffff")		#項目のない部分の背景色＝白
		hPanel.SetAutoLayout(True)
	return hPanel




"""
	ラジオボタン関連サンプルコード
	https://www.python-izm.com/gui/wxpython/wxpython_radiobox/

"""