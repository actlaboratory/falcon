# -*- coding: utf-8 -*-
#View Creator
#Copyright (C) 2019 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import ctypes
import wx
from . import fontManager
import _winxptheme

dll=ctypes.cdll.LoadLibrary("whelper.dll")

class ViewCreator():

	GridSizer = -1
	FlexGridSizer = -2

	# mode=1で白黒反転。その他は白。
	def __init__(self,mode,parent,parentSizer=None,orient=wx.HORIZONTAL,space=0,label=""):
		self.mode=mode
		self.parent=parent
		self.font=fontManager.FontManager()

		self.SetFace(parent)
		if orient==self.FlexGridSizer:
			pass
			#self.sizer=wx.FlexGridSizer()
		elif orient==self.GridSizer:
			pass
			#self.sizer=wx.GridSizer()
		else:
			self.sizer=self.BoxSizer(parentSizer,orient,label,space)
		self.space=space
		self.AddSpace(self.space)

	def AddSpace(self,space=-1):
		if self.sizer.__class__==wx.BoxSizer or self.sizer.__class__==wx.StaticBoxSizer:
			if space==-1:
				space==self.space
			self.sizer.AddSpacer(space)

	#parentで指定したsizerの下に、新たなsizerを設置
	def BoxSizer(self,parent,orient=wx.VERTICAL,label="",space=0):
		if label=="":
			sizer=wx.BoxSizer(orient)
		else:
			sizer=wx.StaticBoxSizer(orient,self.parent,label)
			self.SetFace(sizer.GetStaticBox())
		if (parent!=None):
			parent.Add(sizer,0,wx.ALL,space)
		else:
			self.parent.SetSizer(sizer)
		return sizer


	def button(self,text,event):
		hButton=wx.Button(self.parent, wx.ID_ANY,label=text, name=text)
		hButton.Bind(wx.EVT_BUTTON,event)
		self.SetFace(hButton)
		return hButton

	def okbutton(self,text,event):
		hButton=wx.Button(self.parent, wx.ID_OK,label=text, name=text)
		hButton.Bind(wx.EVT_BUTTON,event)
		self.SetFace(hButton)
		self.sizer.Add(hButton,0,wx.ALIGN_BOTTOM | wx.ALIGN_RIGHT | wx.ALL,5)
		return hButton

	def cancelbutton(self,text,event):
		hButton=wx.Button(self.parent, wx.ID_CANCEL,label=text, name=text)
		hButton.Bind(wx.EVT_BUTTON,event)
		self.SetFace(hButton)
		self.sizer.Add(hButton,0,wx.ALIGN_BOTTOM | wx.ALIGN_RIGHT | wx.ALL,5)
		return hButton

	def checkbox(self,text,event):
		hPanel=wx.Panel(self.parent,wx.ID_ANY,)
		hCheckBox=wx.CheckBox(hPanel,wx.ID_ANY, label=text, name=text)
		hCheckBox.Bind(wx.EVT_CHECKBOX,event)
		self.SetFace(hCheckBox,skip_colour=True)
		hSizer=wx.BoxSizer()
		hSizer.Add(hCheckBox)
		hPanel.SetSizer(hSizer)
		self.sizer.Add(hPanel)
		print("scCheckbox")
		dll.ScCheckbox(hPanel.GetHandle())
		self.AddSpace(self.space)
		return hCheckBox

	def radiobox(self,text,items,event):
		hRadioBox=wx.RadioBox(self.parent,label=text, name=text, choices=items)
		hRadioBox.Bind(wx.EVT_RADIOBOX,event)
		self.SetFace(hRadioBox)
		self.sizer.Add(hRadioBox)
		self.AddSpace(self.space)
		return hRadioBox

	def ListCtrl(self,proportion,sizerFlag,**settings):
		hListCtrl=wx.ListCtrl(self.parent,wx.ID_ANY,**settings)
		self.SetFace(hListCtrl)
		self.sizer.Add(hListCtrl,proportion,sizerFlag)
		self.AddSpace(self.space)
		return hListCtrl

	def inputbox(self,text):
		hStaticText=wx.StaticText(self.parent, -1, label="入力", name="入力")
		hTextCtrl=wx.TextCtrl(self.parent, -1)
		self.SetFace(hTextCtrl)
		self.sizer.Add(hTextCtrl)
		self.AddSpace(self.space)
		return hStaticText,hTextCtrl

	def GetPanel(self):
		return self.parent

	def GetSizer(self):
		return self.sizer

	def SetFace(self,target,skip_colour=False):
		if not skip_colour:
			if self.mode==1:
				target.SetBackgroundColour("#000000")		#背景色＝黒
				target.SetForegroundColour("#ffffff")		#文字色＝白
			else:
				target.SetBackgroundColour("#ffffff")		#背景色＝白
				target.SetForegroundColour("#000000")		#文字色＝黒
			#end else
		#end skip
		target.SetThemeEnabled(False)
		_winxptheme.SetWindowTheme(target.GetHandle(),"","")
		target.SetFont(self.font.GetFont())


#parentで指定したsizerの下に、新たなBoxSizerを設置
def BoxSizer(parent,orient=wx.VERTICAL,flg=0,border=0):
	sizer=wx.BoxSizer(orient)
	if (parent!=None):
		parent.Add(sizer,0,flg,border)
	return sizer


# parentで指定されたフレームにパネルを設置する
# modeはViewCreator.__init__と同様
def makePanel(mode,parent):
	hPanel=wx.Panel(parent,wx.ID_ANY)
	if mode==1:
		#hPanel.SetBackgroundColour("#ffffff")		#項目のない部分の背景色＝黒
		pass
	else:
		#hPanel.SetBackgroundColour("#ffffff")		#項目のない部分の背景色＝白
		#hPanel.SetAutoLayout(True)
		pass
	return hPanel




"""
	ラジオボタン関連サンプルコード
	https://www.python-izm.com/gui/wxpython/wxpython_radiobox/

"""