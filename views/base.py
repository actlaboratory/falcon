# -*- coding: utf-8 -*-
#Falcon app views base class
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import constants
import keymap
import defaultKeymap
import menuItemsStore
from simpleDialog import dialog

import globalVars


class BaseView(object):
	"""falconのビューの基本クラス。"""
	def __init__(self):
		self.SetShortcutEnable=True

	def Initialize(self, ttl, x, y,px,py):
		"""タイトルとウィンドウサイズとポジションを指定して、ウィンドウを初期化する。"""
		self.hFrame=wx.Frame(None,-1,ttl, size=(x,y),pos=(px,py))
		self.hFrame.Bind(wx.EVT_MOVE_END,self.events.WindowMove)
		self.hFrame.Bind(wx.EVT_SIZE,self.events.WindowResize)

	def InstallMenuEvent(self,menu,event):
		"""メニューを作り、指定されたイベント処理用オブジェクトと結びつける。"""
		menu.Apply(self.hFrame,event)
		self.menu=menu

	def SetShortcutEnabled(self,en):
		"""
			ショートカットキーの有効/無効を切り替える。
			AcceleratorTableを空にしないと、名前の変更中にエディットボックスに矢印キーやBSキーの操作がいかない。
			逆に、AcceleratorTableだけを空にしてもメニューバーにあるコマンドが実行されてしまう。
			ということで、両方の対策が必要。
		"""
		t=self.menu.acceleratorTable if en else wx.AcceleratorTable()
		self.hFrame.SetAcceleratorTable(t)
		self.SetShortcutEnable=en
	#end SetShortcutEnabled

class BaseMenu(object):
	def InitShortcut(self,identifier):
		self.keymap=keymap.KeymapHandler(defaultKeymap.defaultKeymap)
		self.keymap.addFile(constants.KEYMAP_FILE_NAME)
		self.keymap_identifier=identifier

	def RegisterMenuCommand(self,menu_handle,ref_id,title):
		shortcut=self.keymap.GetKeyString(self.keymap_identifier,ref_id)
		s=title if shortcut is None else "%s\t%s" % (title,shortcut)
		menu_handle.Append(menuItemsStore.getRef(ref_id),s)

	def ApplyShortcut(self,hFrame):
		self.acceleratorTable=self.keymap.GetTable(self.keymap_identifier)
		hFrame.SetAcceleratorTable(self.acceleratorTable)

class BaseEvents(object):
	"""イベント処理のデフォルトの動作をいくつか定義してあります。"""
	def __init__(self,parent,identifier):
		self.parent=parent
		self.identifier=identifier

	def Exit(self,event):
		self.parent.hFrame.Destroy()

	# wx.EVT_MOVE_END→wx.MoveEvent
	def WindowMove(self,event):
		#設定ファイルに位置を保存
		globalVars.app.config[self.identifier]["positionX"]=self.parent.hFrame.GetPosition().x
		globalVars.app.config[self.identifier]["positionY"]=self.parent.hFrame.GetPosition().x

	# wx.EVT_SIZE→wx.SizeEvent
	def WindowResize(self,event):
		#設定ファイルにサイズを保存
		globalVars.app.config[self.identifier]["sizeX"]=event.GetSize().x
		globalVars.app.config[self.identifier]["sizeY"]=event.GetSize().y

		#sizerを正しく機能させるため、Skipの呼出が必須
		event.Skip()
