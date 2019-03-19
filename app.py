# -*- coding: utf-8 -*-
#Falcon app GUI implementation
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import sys
import os
import gettext
import logging
from logging import getLogger, FileHandler, Formatter
import wx
import configparser
import constants
import tabObjects
import misc
from simpleDialog import *

class falconAppMain(wx.App):

	def initialize(self, ttl, x, y):
		"""タイトルとウィンドウサイズを指定して、ウィンドウを初期化する。"""
		t=misc.Timer()
		self.InitLogger()
		self.LoadSettings()
		self.InitTranslation()
		self.log.debug("finished environment setup (%d milliseconds from start)" % t.elapsed)
		#フレームはウィンドウの中に部品を設置するための枠。
		self.hFrame=wx.Frame(None, -1, ttl,size=(x,y))
		self.SetTopWindow(self.hFrame)
		self.hFrame.Bind(wx.EVT_CLOSE, self.OnExit)
		self.InstallMenu()
		self.InstallListCtrl()
		self.hFrame.SetMenuBar(self.hMenuBar)
		self.tabs=[]
		self.MakeFirstTab()
		self.hFrame.Show()
		self.log.debug("Finished window setup (%d milliseconds from start)" % t.elapsed)
		return True

	def InitLogger(self):
		"""ロギング機能を初期化して準備する。"""
		self.hLogHandler=FileHandler("falcon.log", mode="w", encoding="utf-8")
		self.hLogHandler.setLevel(logging.DEBUG)
		self.hLogFormatter=Formatter("%(name)s - %(levelname)s - %(message)s (%(asctime)s)")
		self.hLogHandler.setFormatter(self.hLogFormatter)
		self.log=getLogger("falcon")
		self.log.setLevel(logging.DEBUG)
		self.log.addHandler(self.hLogHandler)
		self.log.info("Starting Falcon.")

	def LoadSettings(self):
		"""設定ファイルを読み込む。なければデフォルト設定を適用し、設定ファイルを書く。"""
		self.config = configparser.ConfigParser()
		if os.path.exists(constants.SETTING_FILE_NAME):
			self.config.read(constants.SETTING_FILE_NAME)
		else:
			self.config["general"]={"language": "ja-JP"}
			with open(constants.SETTING_FILE_NAME, "w") as f: self.config.write(f)

	def InitTranslation(self):
		"""翻訳を初期化する。"""
		self.translator=gettext.translation("messages","locale", languages=[self.config["general"]["language"]], fallback=True)
		self.translator.install()

	def InstallMenu(self):
		"""メニューバーを作り、フレームに接続する。"""
		#メニューの大項目を作る
		self.hFileMenu=wx.Menu()
		self.hHelpMenu=wx.Menu()
		#今のところ、トップレベルのメニューは30個のスペースを確保してある。つまり、ファイルメニューには30個までの項目を入れられる。
		#ファイルメニューの中身
		self.hFileMenu.Append(constants.MENUITEM_FILE_EXIT,_("終了"))
		#ヘルプメニューの中身
		self.hHelpMenu.Append(constants.MENUITEM_HELP_VERINFO,_("バージョン情報"))
		#メニューバー
		self.hMenuBar=wx.MenuBar()
		self.hMenuBar.Append(self.hFileMenu,_("ファイル"))
		self.hMenuBar.Append(self.hHelpMenu,_("ヘルプ"))
		self.hFrame.SetMenuBar(self.hMenuBar)
		self.hFrame.Bind(wx.EVT_MENU,self.OnMenuSelect)

	def InstallListCtrl(self):
		"""リストコントロールを設定する。"""
		#パネルには複数のコントロールを設置できる。
		self.hListPanel=wx.Panel(self.hFrame, wx.ID_ANY, pos=(0, 0), size=(1000, 400))
		self.hListCtrl=wx.ListCtrl(self.hListPanel, wx.ID_ANY, style=wx.LC_REPORT)

	def MakeFirstTab(self):
		"""最初のタブを作成する。"""
		tab=tabObjects.FileListTab()
		tab.Initialize(os.getcwd())
		self.AppendTab(tab,active=True)

	def AppendTab(self,tab,active=False):
		"""タブを追加する。active=True で、追加したタブをその場でアクティブにする。"""
		self.tabs.append(tab)
		if active is True: self.ActivateTab(tab)

	def ActivateTab(self,tab):
		"""指定されたタブをアクティブにする。内部で管理しているタブリストに入っていない他部でも表示できる。"""
		self.hListCtrl.ClearAll()
		#カラム設定
		i=0
		for elem in tab.GetColumns():
			self.hListCtrl.InsertColumn(i,elem,format=wx.LIST_FORMAT_LEFT,width=wx.LIST_AUTOSIZE)
			i+=1
		#内容設定
		for elem in tab.GetItems():
			self.hListCtrl.Append(elem)

	def OnMenuSelect(self,event):
		"""メニュー項目が選択されたときのイベントハンドら。"""
		selected=event.GetId()#メニュー識別しの数値が出る
		if selected==constants.MENUITEM_FILE_EXIT:
			self.OnExit()
			return
		if selected==constants.MENUITEM_HELP_VERINFO:
			self.ShowVersionInfo()
			return
		dialog(_("エラー"),_("操作が定義されていないメニューです。"))
		return

	def OnExit(self):
		"""アプリケーションを終了させる。"""
		sys.exit()

	def ShowVersionInfo(self):
		"""バージョン情報を表示する。"""
		dialog(_("バージョン情報"),_("%(app)s Version %(ver)s.\nCopyright (C) %(year)s %(names)s") % {"app":constants.APP_NAME, "ver":constants.APP_VERSION, "year":constants.APP_COPYRIGHT_YEAR, "names":constants.APP_DEVELOPERS})
