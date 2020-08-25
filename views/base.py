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
		self.hFrame.Bind(wx.EVT_CLOSE,self.events.Exit)

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

	def PopupMenu(self,hMenu):
		self.hFrame.PopupMenu(hMenu)

class BaseMenu(object):
	def __init__(self):
		self.blockCount={}				#key=intのref、value=blockCount
		self.desableItems=set()			#ブロック中のメニューのrefを格納
		self.hMenuBar=wx.MenuBar()

	def InitShortcut(self,identifier):
		self.keymap=keymap.KeymapHandler(defaultKeymap.defaultKeymap,keymap.KeyFilter().SetDefault(False,True))
		self.keymap_identifier=identifier
		self.keymap.addFile(constants.KEYMAP_FILE_NAME)
		errors=self.keymap.GetError(identifier)
		if errors:
			tmp=_(constants.KEYMAP_FILE_NAME+"で設定されたショートカットキーが正しくありません。キーの重複、存在しないキー名の指定、使用できないキーパターンの指定などが考えられます。以下のキーの設定内容をご確認ください。\n\n")
			for v in errors:
				tmp+=v+"\n"
			dialog(_("エラー"),tmp)

		#これ以降はユーザ設定の追加なのでフィルタを変更
		self.keymap.filter=keymap.KeyFilter().SetDefault(False,False)

	def RegisterMenuCommand(self,menu_handle,ref_id,title="",subMenu=None,index=-1):
		if type(ref_id)==dict:
			for k,v in ref_id.items():
				self._RegisterMenuCommand(menu_handle,k,v,None,index)
		else:
			return self._RegisterMenuCommand(menu_handle,ref_id,title,subMenu,index)

	def _RegisterMenuCommand(self,menu_handle,ref_id,title,subMenu,index):
		if ref_id=="" and title=="":
			if index>=0:
				menu_handle.InsertSeparator()
			else:
				menu_handle.AppendSeparator()
			return
		shortcut=self.keymap.GetKeyString(self.keymap_identifier,ref_id)
		s=title if shortcut is None else "%s\t%s" % (title,shortcut)
		if subMenu==None:
			if index>=0:
				menu_handle.Insert(index,menuItemsStore.getRef(ref_id),s)
			else:
				menu_handle.Append(menuItemsStore.getRef(ref_id),s)
		else:
			if index>=0:
				menu_handle.Insert(index,menuItemsStore.getRef(ref_id),s,subMenu)
			else:
				menu_handle.Append(menuItemsStore.getRef(ref_id),s,subMenu)
		self.blockCount[menuItemsStore.getRef(ref_id)]=0

	def ApplyShortcut(self):
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
			メニュー項目のブロック事由が消滅したので、ブロックカウントを減らす。0になったら有効化する
			refはリスト
		"""
		for i in ref:
			try:
				self.blockCount[menuItemsStore.getRef(i)]-=1
			except KeyError:
				self.blockCount[menuItemsStore.getRef(i)]=0

			#ブロック解除
			if self.blockCount[menuItemsStore.getRef(i)]==0 and i not in self.desableItems:
				self.hMenuBar.Enable(menuItemsStore.getRef(i),True)

	def Enable(self,ref,enable):
		if enable:
			self.desableItems.add(ref)
		else:
			self.desableItems.discard(ref)
		self.hMenuBar.Enable(ref,self.blockCount[ref]==0 and ref not in self.desableItems)

	def IsEnable(self,ref):
		return self.blockCount[menuItemsStore.getRef(ref)]<=0

class BaseEvents(object):
	"""イベント処理のデフォルトの動作をいくつか定義してあります。"""
	def __init__(self,parent,identifier):
		self.parent=parent
		self.identifier=identifier

	def Exit(self,event=None):
		self.parent.hFrame.Close()

	# wx.EVT_MOVE_END→wx.MoveEvent
	def WindowMove(self,event):
		#設定ファイルに位置を保存
		globalVars.app.config[self.identifier]["positionX"]=self.parent.hFrame.GetPosition().x
		globalVars.app.config[self.identifier]["positionY"]=self.parent.hFrame.GetPosition().y

	# wx.EVT_SIZE→wx.SizeEvent
	def WindowResize(self,event):
		#ウィンドウがアクティブでない時(ウィンドウ生成時など)のイベントは無視
		if self.parent.hFrame.IsActive():
			#最大化状態でなければ、設定ファイルにサイズを保存
			if not self.parent.hFrame.IsMaximized():
				globalVars.app.config[self.identifier]["sizeX"]=event.GetSize().x
				globalVars.app.config[self.identifier]["sizeY"]=event.GetSize().y

			#設定ファイルに最大化状態か否かを保存
			globalVars.app.config[self.identifier]["maximized"]=self.parent.hFrame.IsMaximized()

		#sizerを正しく機能させるため、Skipの呼出が必須
		event.Skip()

