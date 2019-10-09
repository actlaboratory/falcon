# -*- coding: utf-8 -*-
#Falcon app main view
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import gettext
import logging
import os
import sys
import wx
from logging import getLogger, FileHandler, Formatter
from simpleDialog import dialog

from .base import *
import misc
import views.test
import views.fonttest
import views.changeAttribute
import constants
import errorCodes
import globalVars
import listObjects
import tabObjects
import menuItemsStore
from simpleDialog import *
import ctypes

class View(BaseView):
	def Initialize(self):
		t=misc.Timer()
		self.identifier="mainView"#このビューを表す文字列
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("created")
		self.app=globalVars.app
		self.events=Events(self,self.identifier)
		title=""
		if(ctypes.windll.shell32.IsUserAnAdmin()):
			title+="["+_("管理者")+"]"
		title+=constants.APP_NAME
		super().Initialize(
			title,
			self.app.config.getint(self.identifier,"sizeX",800),
			self.app.config.getint(self.identifier,"sizeY",600),
			self.app.config.getint(self.identifier,"positionX"),
			self.app.config.getint(self.identifier,"positionY")
		)
		self.menu=Menu()
		self.InstallMenuEvent(self.menu,self.events)
		self.InstallShortcutEvent(self.identifier,self.events)
		self.InstallListPanel()
		self.tabs=[]
		self.MakeFirstTab()
		self.hFrame.Show()
		self.app.SetTopWindow(self.hFrame)
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def InstallListPanel(self):
		"""リストコントロールが表示されるパネルを設定する。"""
		self.hListPanel=wx.Panel(self.hFrame, wx.ID_ANY, pos=(0,0),size=(800,300))
		self.hListPanel.SetBackgroundColour("#0000ff")		#項目のない部分の背景色
		self.hListPanel.SetAutoLayout(True)
		self.sizer=wx.BoxSizer(wx.HORIZONTAL)
		self.hListPanel.SetSizer(self.sizer)

	def MakeFirstTab(self):
		"""最初のタブを作成する。"""
		self.activeTab=None#最初なのでなにもなし
		tab=tabObjects.MainListTab()
		tab.Initialize(self)
		lst=listObjects.FileList()
		if(len(sys.argv)>1 and os.path.isdir(os.path.expandvars(sys.argv[1]))):
			lst=listObjects.FileList()
			lst.Initialize(os.path.expandvars(sys.argv[1]))
		elif(self.app.config["browse"]["startPath"]==""):
			lst=listObjects.DriveList()
			lst.Initialize()
		elif(os.path.isdir(os.path.expandvars(self.app.config["browse"]["startPath"]))):
			lst=listObjects.FileList()
			lst.Initialize(os.path.expandvars(self.app.config["browse"]["startPath"]))
		else:
			lst=listObjects.DriveList()
			lst.Initialize()
		if(len(sys.argv)>1 and not os.path.isdir(os.path.expandvars(sys.argv[1]))):
			dialog("Error",_("引数で指定されたディレクトリ '%(dir)s' は存在しません。") % {"dir": sys.argv[1]})
		tab.Update(lst)
		self.AppendTab(tab,active=True)

	def AppendTab(self,tab,active=False):
		"""タブを追加する。active=True で、追加したタブをその場でアクティブにする。"""
		self.tabs.append(tab)
		self.sizer.Add(tab.GetListCtrl(),1,wx.EXPAND)
		self.log.debug("A new tab has been added (now %d)" % len(self.tabs))
		if active is True: self.ActivateTab(tab)

	def ActivateTab(self,tab):
		"""指定されたタブをアクティブにする。内部で管理しているタブリストに入っていない他部でも表示できる。"""
		if self.activeTab: self.activeTab.getListCtrl().Hide()
		self.activeTab=tab
		l=self.activeTab.GetListCtrl()
		l.Show(True)

class Menu():
	def Apply(self,target,event):
		"""指定されたウィンドウに、メニューを適用する。"""
		#メニューの大項目を作る
		self.hFileMenu=wx.Menu()
		self.hEditMenu=wx.Menu()
		self.hMoveMenu=wx.Menu()
		self.hReadMenu=wx.Menu()
		self.hToolMenu=wx.Menu()
		self.hViewMenu=wx.Menu()
		self.hEnvMenu=wx.Menu()
		self.hHelpMenu=wx.Menu()
		#ファイルメニューの中身
		self.hFileMenu.Append(menuItemsStore.getRef("FILE_RENAME"),_("名前を変更"))
		self.hFileMenu.Append(menuItemsStore.getRef("FILE_CHANGEATTRIBUTE"),_("属性を変更"))
		self.hFileMenu.Append(menuItemsStore.getRef("FILE_EXIT"),_("終了"))
		#ファイルメニューの中身
		self.hEditMenu.Append(menuItemsStore.getRef("EDIT_SORTNEXT"),_("次の並び順\tShift+F1"))
		self.hEditMenu.Append(menuItemsStore.getRef("EDIT_SORTSELECT"),_("並び順を選択\tCtrl+S"))
		self.hEditMenu.Append(menuItemsStore.getRef("EDIT_SORTCYCLEAD"),_("昇順/降順切り替え\tShift+F11"))
		self.hEditMenu.Append(menuItemsStore.getRef("EDIT_UPDATEFILELIST"),_("最新の情報に更新\tF5"))
		#移動メニューの中身
		self.hMoveMenu.Append(menuItemsStore.getRef("MOVE_FORWARD"),_("開く\tEnter"))
		self.hMoveMenu.Append(menuItemsStore.getRef("MOVE_FORWARD_ADMIN"),_("管理者として開く"))
		self.hMoveMenu.Append(menuItemsStore.getRef("MOVE_FORWARD_STREAM"),_("開く(ストリーム)"))
		self.hMoveMenu.Append(menuItemsStore.getRef("MOVE_BACKWARD"),_("上の階層へ\tBackSpace"))
		#環境メニューの中身
		self.hEnvMenu.Append(menuItemsStore.getRef("ENV_TESTDIALOG"),_("テストダイアログを表示"))
		self.hEnvMenu.Append(menuItemsStore.getRef("ENV_FONTTEST"),_("フォントテストダイアログを表示"))
		#ヘルプメニューの中身
		self.hHelpMenu.Append(menuItemsStore.getRef("HELP_VERINFO"),_("バージョン情報"))
		#メニューバー
		self.hMenuBar=wx.MenuBar()
		self.hMenuBar.Append(self.hFileMenu,_("ファイル"))
		self.hMenuBar.Append(self.hEditMenu,_("編集"))
		self.hMenuBar.Append(self.hMoveMenu,_("移動"))
		self.hMenuBar.Append(self.hReadMenu,_("読み"))
		self.hMenuBar.Append(self.hToolMenu,_("ツール"))
		self.hMenuBar.Append(self.hViewMenu,_("表示"))
		self.hMenuBar.Append(self.hEnvMenu,_("環境"))
		self.hMenuBar.Append(self.hHelpMenu,_("ヘルプ"))
		target.SetMenuBar(self.hMenuBar)
		target.Bind(wx.EVT_MENU,event.OnMenuSelect)

class Events(BaseEvents):
	def OnMenuSelect(self,event):
		"""メニュー項目が選択されたときのイベントハンドら。"""
		selected=event.GetId()#メニュー識別しの数値が出る
		if selected==menuItemsStore.getRef("MOVE_BACKWARD"):
			self.GoBackward()
			return
		if selected==menuItemsStore.getRef("MOVE_FORWARD"):
			self.GoForward(False)
			return
		if selected==menuItemsStore.getRef("MOVE_FORWARD_ADMIN"):
			self.GoForward(False,admin=True)
			return
		if selected==menuItemsStore.getRef("MOVE_FORWARD_STREAM"):
			self.GoForward(True)
			return
		if selected==menuItemsStore.getRef("EDIT_SORTNEXT"):
			self.SortNext()
			return
		if selected==menuItemsStore.getRef("EDIT_SORTSELECT"):
			self.SortSelect()
			return
		if selected==menuItemsStore.getRef("EDIT_SORTCYCLEAD"):
			self.SortCycleAd()
			return
		if selected==menuItemsStore.getRef("EDIT_UPDATEFILELIST"):
			self.UpdateFilelist()
			return
		if selected==menuItemsStore.getRef("FILE_CHANGEATTRIBUTE"):
			d=views.changeAttribute.Dialog()
			d.Initialize()
			ret=d.Show()
			if ret==wx.ID_CANCEL: return
			dialog("test","%d" % d.GetValue())
			d.Destroy()
			return
		if selected==menuItemsStore.getRef("ENV_TESTDIALOG"):
			self.testdialog=views.test.View()
			self.testdialog.Initialize()
			self.testdialog.Show()
			return
		if selected==menuItemsStore.getRef("ENV_FONTTEST"):
			self.fonttest=views.fonttest.View()
			self.fonttest.Initialize()
			return
		if selected==menuItemsStore.getRef("FILE_RENAME"):
			self.StartRename()
			return
		if selected==menuItemsStore.getRef("FILE_EXIT"):
			self.Exit(event)
			return
		if selected==menuItemsStore.getRef("HELP_VERINFO"):
			self.ShowVersionInfo()
			return
		dialog(_("エラー"),_("操作が定義されていないメニューです。"))
		return

	def StartRename(self):
		"""リネームを開始する。"""
		self.parent.activeTab.StartRename()
	#end StartRename

	def ShowVersionInfo(self):
		"""バージョン情報を表示する。"""
		dialog(_("バージョン情報"),_("%(app)s Version %(ver)s.\nCopyright (C) %(year)s %(names)s") % {"app":constants.APP_NAME, "ver":constants.APP_VERSION, "year":constants.APP_COPYRIGHT_YEAR, "names":constants.APP_DEVELOPERS})

	def GoBackward(self):
		"""back アクションを実行"""
		p=self.parent
		ret=p.activeTab.TriggerAction(tabObjects.ACTION_BACKWARD)
		if ret==errorCodes.NOT_SUPPORTED:
			dialog(_("エラー"),_("このオペレーションはサポートされていません。"))
		elif ret==errorCodes.BOUNDARY:
			pass
			# play sound here.

	def GoForward(self,stream,admin=False):
		"""forward アクションを実行。stream=True で、ファイルを開く代わりにストリームを開く。admin=True で、管理者モード。"""
		p=self.parent
		act=tabObjects.ACTION_FORWARD if stream is False else tabObjects.ACTION_FORWARD_STREAM
		ret=p.activeTab.TriggerAction(act,admin)
		if ret==errorCodes.NOT_SUPPORTED:
			dialog(_("エラー"),_("このオペレーションはサポートされていません。"))
		elif ret==errorCodes.BOUNDARY:
			dialog("test","mada")

	def SortNext(self):
		"""sortNext アクションを実行。"""
		p=self.parent
		act=tabObjects.ACTION_SORTNEXT
		ret=p.activeTab.TriggerAction(act)
		if ret==errorCodes.NOT_SUPPORTED:
			dialog(_("エラー"),_("このオペレーションはサポートされていません。"))

	def SortSelect(self):
		"""並び順を指定する。"""
		t=self.parent.activeTab
		t.SortSelect()

	def SortCycleAd(self):
		t=self.parent.activeTab
		t.SortCycleAd()

	def UpdateFilelist(self):
		ret=self.parent.activeTab.UpdateFilelist()

