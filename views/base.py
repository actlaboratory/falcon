# -*- coding: utf-8 -*-
#Falcon app views base class
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import constants
import keymap
import defaultKeymap
import menuItemsStore
import views.ViewCreator
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

		self.hPanel=views.ViewCreator.makePanel(self.hFrame)
		self.creator=views.ViewCreator.ViewCreator(1,self.hPanel,None)

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
		self.activeTab.hListCtrl.SetAcceleratorTable(t)
		self.SetShortcutEnable=en
	#end SetShortcutEnabled

class BaseMenu(object):
	def __init__(self):
		self.blockCount={}

	def InitShortcut(self,identifier):
		self.keymap=keymap.KeymapHandler(defaultKeymap.defaultKeymap)
		self.keymap_identifier=identifier
		self.keymap.addFile(constants.KEYMAP_FILE_NAME)
		errors=self.keymap.GetError(identifier)
		if errors:
			tmp=_(constants.KEYMAP_FILE_NAME+"で設定されたショートカットキーが正しくありません。キーが重複しているか、存在しないキー名を指定しています。以下のキーの設定内容をご確認ください。\n\n")
			for v in errors:
				tmp+=v+"\n"
			dialog(_("エラー"),tmp)

	def RegisterMenuCommand(self,menu_handle,ref_id,title):
		shortcut=self.keymap.GetKeyString(self.keymap_identifier,ref_id)
		s=title if shortcut is None else "%s\t%s" % (title,shortcut)
		menu_handle.Append(menuItemsStore.getRef(ref_id),s)
		self.blockCount[menuItemsStore.getRef(ref_id)]=0

	def ApplyShortcut(self,hFrame):
		self.acceleratorTable=self.keymap.GetTable(self.keymap_identifier)

	def Block(self,ref):
		"""
			メニュー項目の利用をブロックし、無効状態にする
			refはリスト
		"""
		for i in ref:
			try:
				self.blockCount[menuItemsStore.getRef(i)]+=1
			except KeyError:
				self.blockCount[menuItemsStore.getRef(i)]=1

			#新規にブロック
			if self.blockCount[menuItemsStore.getRef(i)]==1:
				self.hMenuBar.Enable(menuItemsStore.getRef(i),False)

	def UnBlock(self,ref):
		"""
			メニュー項目のブロック自由が消滅したので、ブロックカウントを減らす。0になったら有効化する
			refはリスト
		"""
		for i in ref:
			try:
				self.blockCount[menuItemsStore.getRef(i)]-=1
			except KeyError:
				self.blockCount[menuItemsStore.getRef(i)]=0

			#ブロック解除
			if self.blockCount[menuItemsStore.getRef(i)]==0:
				self.hMenuBar.Enable(menuItemsStore.getRef(i),True)

class BaseEvents(object):
	"""イベント処理のデフォルトの動作をいくつか定義してあります。"""
	def __init__(self,parent,identifier):
		self.parent=parent
		self.identifier=identifier

	def Exit(self,event=None):
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
