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

from . import navigator

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

	def ApplyShortcut(self,hFrame):
		self.acceleratorTable=self.keymap.GetTable(self.keymap_identifier)

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

	def GoForward(self,stream,admin=False):
		"""選択中のフォルダに入るか、選択中のファイルを実行する。stream=True の場合、ファイルの NTFS 副ストリームを開く。"""
		index=self.GetFocusedItem()
		elem=self.listObject.GetElement(index)
		if isinstance(elem,browsableObjects.Folder):#このフォルダを開く
			#TODO: 管理者モードだったら、別のfalconが昇格して開くように
			r=navigator.Navigate(elem.fullpath)
		#end フォルダ開く
		elif isinstance(elem,browsableObjects.File):#このファイルを開く
			if not stream:
				misc.RunFile(elem.fullpath,admin)
				return
			#end runFile
			#TODO: 管理者として副ストリーム…まぁ、使わないだろうけど一貫性のためには開くべきだと思う
			if stream:
				r=navigator.Navigate(elem.fullpath)
		#end ファイルを開く
		#end なにを開くか
		return errorCodes.OK if self is r else r

	def GoBackward(self):
		"""内包しているフォルダ/ドライブ一覧へ移動する。"""
		if len(self.listObject.rootDirectory)<=3:		#ドライブリストへ
			target=""
			cursorTarget=self.listObject.rootDirectory[0]
		else:
			target=os.path.split(self.listObject.rootDirectory)[0]
			cursorTarget=os.path.split(self.listObject.rootDirectory)[1]
		return self.move(target,cursorTarget)
