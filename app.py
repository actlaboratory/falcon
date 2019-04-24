# -*- coding: utf-8 -*-
#Falcon app GUI implementation
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import configparser
import gettext
import logging
import os
import sys
import wx
from logging import getLogger, FileHandler, Formatter

import constants
import DefaultSettings
import errorCodes
import keymap
import misc
import tabObjects
from simpleDialog import *

class falconAppMain(wx.App):

	def initialize(self, ttl):
		"""タイトルとウィンドウサイズを指定して、ウィンドウを初期化する。"""
		t=misc.Timer()
		self.InitLogger()
		self.LoadSettings()
		self.InitTranslation()
		self.log.debug("finished environment setup (%f seconds from start)" % t.elapsed)
		#フレームはウィンドウの中に部品を設置するための枠。
		self.hFrame=wx.Frame(None, -1, ttl,size=(self.config.getint("MainView","sizeX"),self.config.getint("MainView","sizeY")))
		self.hFrame.Bind(wx.EVT_CLOSE, self.OnExit)
		self.InstallMenu()
		self.InstallShortcut()
		self.hFrame.SetMenuBar(self.hMenuBar)
		self.InstallListPanel()
		self.tabs=[]
		self.MakeFirstTab()
		self.hFrame.Show()
		self.SetTopWindow(self.hFrame)
		self.log.debug("Finished window setup (%f seconds from start)" % t.elapsed)
		return True

	def InitLogger(self):
		"""ロギング機能を初期化して準備する。"""
		self.hLogHandler=FileHandler("falcon.log", mode="w", encoding="UTF-8")
		self.hLogHandler.setLevel(logging.DEBUG)
		self.hLogFormatter=Formatter("%(name)s - %(levelname)s - %(message)s (%(asctime)s)")
		self.hLogHandler.setFormatter(self.hLogFormatter)
		self.log=getLogger("falcon")
		self.log.setLevel(logging.DEBUG)
		self.log.addHandler(self.hLogHandler)
		self.log.info("Starting Falcon.")

	def InitKeyHandler(self):
		"""キーハンドラを初期化する。"""
		self.log.debug("Initializing keyHandler...")
		self.keyHandler=keyHandler.KeyHandler()
		self.keyHandler.Initialize()

	def LoadSettings(self):
		"""設定ファイルを読み込む。なければデフォルト設定を適用し、設定ファイルを書く。"""
		self.config = DefaultSettings.DefaultSettings.get()
		if os.path.exists(constants.SETTING_FILE_NAME):
			self.config.read(constants.SETTING_FILE_NAME)
		with open(constants.SETTING_FILE_NAME, "w") as f: self.config.write(f)

	def InitTranslation(self):
		"""翻訳を初期化する。"""
		self.translator=gettext.translation("messages","locale", languages=[self.config["general"]["language"]], fallback=True)
		self.translator.install()

	def InstallMenu(self):
		"""メニューバーを作り、フレームに接続する。"""
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
		self.hFileMenu.Append(constants.MENU_ITEMS["FILE_EXIT"].GetValue(),_("終了"))
		#移動メニューの中身
		self.hMoveMenu.Append(constants.MENU_ITEMS["MOVE_FORWARD"].GetValue(),_("開く"))
		self.hMoveMenu.Append(constants.MENU_ITEMS["MOVE_BACKWARD"].GetValue(),_("閉じる"))
		#ヘルプメニューの中身
		self.hHelpMenu.Append(constants.MENU_ITEMS["HELP_VERINFO"].GetValue(),_("バージョン情報"))
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
		self.hFrame.SetMenuBar(self.hMenuBar)
		self.hFrame.Bind(wx.EVT_MENU,self.OnMenuSelect)

	def InstallShortcut(self):
		"""アクセラレーターテーブルを設定する。"""
		self.keymap=keymap.KeymapHandler()
		self.keymap.Initialize(constants.KEYMAP_FILE_NAME)
		self.hFrame.SetAcceleratorTable(self.keymap.GenerateTable())

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
		tab=tabObjects.FileListTab()
		tab.Initialize(self.hListPanel, os.path.expandvars(self.config["Browse"]["startPath"]))
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

	def OnMenuSelect(self,event):
		"""メニュー項目が選択されたときのイベントハンドら。"""
		selected=event.GetId()#メニュー識別しの数値が出る
		self.log.debug("Menu item selected (identifier %d)" % selected)
		if selected==constants.MENU_ITEMS["FILE_EXIT"].GetValue():
			self.OnExit()
			return
		if selected==constants.MENU_ITEMS["HELP_VERINFO"].GetValue():
			self.ShowVersionInfo()
			return
		self.log.warning("Menu identifier %d is undefined in OnMenuSelect." % selected)
		dialog(_("エラー"),_("操作が定義されていないメニューです。"))
		return

	def OnKeyDown(self,event):
		"""キーが押されたときのコールバック。"""
		self.keyHandler.ProcessKeyDown(event)

	def OnKeyUp(self,event):
		"""キーが離されたときのコールバック。"""
		self.keyHandler.ProcessKeyUp(event)

	def OnExit(self, event=None):
		"""アプリケーションを終了させる。"""
		self.log.info("Exiting Falcon...")
		self.log.info("Bye bye!")
		sys.exit()

	def ShowVersionInfo(self):
		"""バージョン情報を表示する。"""
		dialog(_("バージョン情報"),_("%(app)s Version %(ver)s.\nCopyright (C) %(year)s %(names)s") % {"app":constants.APP_NAME, "ver":constants.APP_VERSION, "year":constants.APP_COPYRIGHT_YEAR, "names":constants.APP_DEVELOPERS})

	def TriggerBackwardAction(self):
		"""back アクションを実行"""
		ret=self.activeTab.TriggerAction(self.hListCtrl.GetFocusedItem(),tabObjects.ACTION_BACKWARD)
		if ret==errorCodes.NOT_SUPPORTED:
			dialog(_("エラー"),_("このオペレーションはサポートされていません。"))
		elif ret==errorCodes.BOUNDARY:
			dialog("test","mada")
		else:
			self.UpdateList()

	def TriggerForwardAction(self):
		"""forward アクションを実行"""
		ret=self.activeTab.TriggerAction(self.hListCtrl.GetFocusedItem(),tabObjects.ACTION_FORWARD)
		if ret==errorCodes.NOT_SUPPORTED:
			dialog(_("エラー"),_("このオペレーションはサポートされていません。"))
		elif ret==errorCodes.BOUNDARY:
			dialog("test","mada")
		else:
			self.UpdateList()
