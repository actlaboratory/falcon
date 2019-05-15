# -*- coding: utf-8 -*-
#View Creator
#Copyright (C) 2019 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx

class ViewCreator():



	# mode=1で白黒反転。その他は白。
	def __init__(self,mode,parent):
		self.mode=mode
		if isinstance(parent,wx.Panel):
			self.hPanel=parent
		else:
			self.hPanel=makePanel(mode,parent)

	def button(self,text,event):
		hButton=wx.Button(self.hPanel, wx.ID_ANY,text)
		hButton.Bind(wx.EVT_BUTTON,event)
		if self.mode==1:
			hButton.SetBackgroundColour("#222222")		#背景色＝グレー
			hButton.SetForegroundColour("#ffffff")		#文字色＝白
		else:
			hButton.SetBackgroundColour("#eeeeee")		#背景色＝白
			hButton.SetForegroundColour("#000000")		#文字色＝黒
		return hButton

	def checkbox(self,text,event):
		hCheckBox=wx.CheckBox(self.hPanel,wx.ID_ANY,text)
		hCheckBox.Bind(wx.EVT_CHECKBOX,event)
		if self.mode==1:
			hCheckBox.SetBackgroundColour("#222222")	#背景色＝グレー
			hCheckBox.SetForegroundColour("#ffffff")	#文字色＝白
		else:
			hCheckBox.SetBackgroundColour("#eeeeee")	#背景色＝白
			hCheckBox.SetForegroundColour("#000000")	#文字色＝黒
		return hCheckBox

	def radiobox(self,text,items,event):
		hRadioBox=wx.RadioBox(self.hPanel,label=text,choices=items)
		hRadioBox.Bind(wx.EVT_RADIOBOX,event)
		if self.mode==1:
			hRadioBox.SetBackgroundColour("#000000")	#背景色＝黒
			hRadioBox.SetForegroundColour("#ffffff")	#文字色＝白
		else:
			hRadioBox.SetBackgroundColour("#ffffff")	#背景色＝白
			hRadioBox.SetForegroundColour("#000000")	#文字色＝黒
		return hRadioBox

	def inputbox(self,text):
		hStaticText=wx.StaticText(self.hPanel, -1, "入力")
		hTextCtrl=wx.TextCtrl(self.hPanel, -1)
		if self.mode==1:
			hTextCtrl.SetBackgroundColour("#222222")	#背景色＝グレー
			hTextCtrl.SetForegroundColour("#ffffff")	#文字色＝白
		else:
			hTextCtrl.SetBackgroundColour("#eeeeee")	#背景色＝白
			hTextCtrl.SetForegroundColour("#000000")	#文字色＝黒
		return hStaticText,hTextCtrl

	def getPanel(self):
		return self.hPanel


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