# -*- coding: utf-8 -*-
#Falcon app views base class
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import constants
import keymap
class BaseView(object):
	"""falconのビューの基本クラス。"""
	def __init__(self):
		pass

	def Initialize(self, ttl, x, y):
		"""タイトルとウィンドウサイズを指定して、ウィンドウを初期化する。"""
		self.hFrame=wx.Frame(None,-1, ttl, size=(x,y))

	def InstallMenuEvent(self,menu,event):
		"""メニューを作り、指定されたイベント処理用オブジェクトと結びつける。"""
		menu.Apply(self.hFrame,event)

	def InstallShortcutEvent(self,identifier,event):
		"""指定されたビューのショートカットキーを読み込んで、イベント処理用クラスと結びつける。"""
		self.keymap=keymap.KeymapHandler()
		self.keymap.Initialize(constants.KEYMAP_FILE_NAME)
		self.hFrame.SetAcceleratorTable(self.keymap.GenerateTable(identifier))

class BaseEvents(object):
	"""イベント処理のデフォルトの動作をいくつか定義してあります。"""
	def __init__(self,parent):
		self.parent=parent

	def Exit(self,event):
		self.parent.hFrame.Destroy()
