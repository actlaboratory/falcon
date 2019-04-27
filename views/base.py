# -*- coding: utf-8 -*-
#Falcon app views base class
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

class View(object):
		"""falconのビューの基本クラス。"""
	def __init__(self):
		pass

	def Initialize(self, ttl, x, y):
		"""タイトルとウィンドウサイズを指定して、ウィンドウを初期化する。"""

def InstallMenuEvent(self,menu):
		"""メニューを作り、指定されたイベント処理用オブジェクトと結びつける。"""
		menu.Apply(self.hFrame,event)

	def InstallShortcutEvent(self,identifier,event):
		"""指定されたビューのショートカットキーを読み込んで、イベント処理用クラスと結びつける。"""
		self.keymap=keymap.KeymapHandler()
		self.keymap.Initialize(constants.KEYMAP_FILE_NAME)
		self.hFrame.SetAcceleratorTable(self.keymap.GenerateTable(identifier))
