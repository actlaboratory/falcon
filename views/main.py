# -*- coding: utf-8 -*-
#Falcon app main view
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import logging
import os
import sys
import wx
import re
import ctypes
import pywintypes

import browsableObjects
import misc
import constants
import errorCodes
import globalVars
import lists
import tabs.navigator
import menuItemsStore
import fileSystemManager
import deviceCtrl

import views.fonttest
import views.changeAttribute
import views.mkdir
import views.makeShortcut
import views.objectDetail
import views.search
import views.makeHash

import workerThreads
import workerThreadTasks

from logging import getLogger, FileHandler, Formatter
from simpleDialog import dialog
from .base import *

from simpleDialog import *

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
		self.menu.InitShortcut(self.identifier)

		#お気に入りフォルダと「ここで開く」のショートカットキーを登録
		for target in (globalVars.app.userCommandManagers):
			for v in target.keyMap:
				self.menu.keymap.add(self.identifier,target.refHead+v,target.keyMap[v])
		errors=self.menu.keymap.GetError(self.identifier)
		if errors:
			tmp=_("お気に入りディレクトリもしくは「ここで開く」で設定されたショートカットキーが正しくありません。キーが重複しているか、存在しないキー名を指定しています。以下のキーの設定内容をご確認ください。\n\n")
			for v in errors:
				tmp+=v+"\n"
			dialog(_("エラー"),tmp)

		self.InstallMenuEvent(self.menu,self.events)

		self.tabs=[]
		self.activeTab=None#最初なので空
		self.hTabCtrl=self.creator.tabCtrl(_("タブ選択"),self.ChangeTab,0,1,wx.EXPAND)
		self.MakeFirstTab()

		self.hFrame.Show()
		self.app.SetTopWindow(self.hFrame)
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def MakeFirstTab(self):
		"""最初のタブを作成する。"""
		if len(sys.argv)>1 and os.path.isdir(os.path.expandvars(sys.argv[1])):
			self.Navigate(os.path.expandvars(sys.argv[1]),as_new_tab=True)
		elif self.app.config["browse"]["startPath"]=="":
			self.Navigate("",as_new_tab=True)
		elif os.path.isdir(os.path.expandvars(self.app.config["browse"]["startPath"])):
			self.Navigate(os.path.expandvars(self.app.config["browse"]["startPath"]),as_new_tab=True)
		else:
			self.Navigate("",as_new_tab=True)
		#end どこを開くか
		if(len(sys.argv)>1 and not os.path.isdir(os.path.expandvars(sys.argv[1]))):
			dialog("Error",_("引数で指定されたディレクトリ '%(dir)s' は存在しません。") % {"dir": sys.argv[1]})
		#end エラー
	#end makeFirstTab

	def Navigate(self,target,as_new_tab=False):
		"""指定のパスにナビゲートする。"""
		self.log.debug("Creating new tab %s..." % target)
		hPanel=views.ViewCreator.makePanel(self.hTabCtrl)
		creator=views.ViewCreator.ViewCreator(1,hPanel,None)
		newtab=tabs.navigator.Navigate(target,create_new_tab_info=(self,creator))
		newtab.hListCtrl.SetAcceleratorTable(self.menu.acceleratorTable)
		self.tabs.append(newtab)
		self.hTabCtrl.InsertPage(len(self.tabs)-1,hPanel,"tab%d" % (len(self.tabs)),False)
		self.ActivateTab(len(self.tabs)-1)

	def ReplaceCurrentTab(self,newtab):
		"""現在のタブのインスタンスを入れ替える。ファイルリストからドライブリストになったときなどに使う。"""
		i=0
		for elem in self.tabs:
			if elem is self.activeTab: break
			i+=1
		#end インデックス調べる

		#environmentの内容を引き継ぐ
		newtab.SetEnvironment(self.activeTab.environment)

		#メニューのブロック情報を変更
		self.menu.Block(newtab.blockMenuList)
		self.menu.UnBlock(self.activeTab.blockMenuList)
		self.menu.hMenuBar.Enable(menuItemsStore.getRef("MOVE_MARK"),newtab.IsMarked())

		self.tabs[i]=newtab
		self.activeTab=newtab
		newtab.ItemSelected()		#メニューのブロック情報を選択中アイテム数の状況に合わせるために必用
	#end ReplaceCurrentTab

	def ActivateTab(self,pageNo):
		"""指定されたインデックスのタブをアクティブにする。"""

		#メニューのブロック状態を変更
		if self.activeTab:
			self.menu.UnBlock(self.activeTab.blockMenuList)
		self.menu.Block(self.tabs[pageNo].blockMenuList)
		self.menu.hMenuBar.Enable(menuItemsStore.getRef("MOVE_MARK"),self.tabs[pageNo].IsMarked())

		self.activeTab=self.tabs[pageNo]
		self.hTabCtrl.SetSelection(pageNo)
		self.activeTab.hListCtrl.SetFocus()

		self.activeTab.ItemSelected()		#メニューのブロック情報を選択中アイテム数の状況に合わせるために必用


	def CloseTab(self,pageNo):
		"""指定されたインデックスのタブを閉じる。閉じたタブがアクティブだった場合は、別のタブをアクティブ状態にする。全てのタブが閉じられた場合は、終了イベントを投げる。"""
		if not isinstance(pageNo,int):#数字じゃなくてタブオブジェクトが渡ってた
			found=-1
			for i in range(len(self.tabs)):
				if self.tabs[i] is pageNo:
					found=i
					break
				#end if
			#end for
			if found==-1: return
			pageNo=found
		#end ページ番号じゃなかったときの検索

		popped_tab=self.tabs.pop(pageNo)
		if len(self.tabs)==0:#タブがなくなった
			self.events.Exit()
			return
		#タブがなくなったらソフト終了
		self.hTabCtrl.DeletePage(pageNo)#この時点で、 noteBook がリストコントロールをデリートするらしいので、他の場所で明示的に消してはいけないとリファレンスに書いてある
		self.hTabCtrl.SendSizeEvent()
		if self.activeTab is popped_tab:#アクティブなタブを閉じた
			new_pageNo=pageNo
			if new_pageNo>=len(self.tabs): new_pageNo=len(self.tabs)-1
			self.ActivateTab(new_pageNo)
		#end アクティブタブを閉じた場合に後ろのタブを持って来る

	#end closeTab

	def ChangeTab(self,event):
		"""タブ変更イベント"""
		pageNo=event.GetSelection()
		self.ActivateTab(pageNo)

	def SetShortcutEnabled(self,en):
		super().SetShortcutEnabled(en)
		if en:
			#通常のメニューバーに戻す
			self.hFrame.SetMenuBar(self.menu.hMenuBar)
		else:
			#名前の変更中にはダミーのメニューバーを出しておく
			#これがないとメニューバーの高さ分リストオブジェクトの大きさが変わってしまうために必要
			self.hFrame.SetMenuBar(self.menu.hDisableMenuBar)
		#SetMenuBarの後に呼び出しが必要
		self.creator.GetSizer().Layout()


class Menu(BaseMenu):
	def __init__(self):
		super().__init__()

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
		self.RegisterMenuCommand(self.hFileMenu,"FILE_RENAME",_("名前を変更"))
		self.RegisterMenuCommand(self.hFileMenu,"FILE_CHANGEATTRIBUTE",_("属性を変更"))
		self.RegisterMenuCommand(self.hFileMenu,"FILE_MAKESHORTCUT",_("ショートカットを作成"))
		self.RegisterMenuCommand(self.hFileMenu,"FILE_TRASH",_("ゴミ箱へ移動"))
		self.RegisterMenuCommand(self.hFileMenu,"FILE_DELETE",_("完全削除"))
		self.RegisterMenuCommand(self.hFileMenu,"FILE_VIEW_DETAIL",_("詳細情報を表示"))
		self.RegisterMenuCommand(self.hFileMenu,"FILE_SHOWPROPERTIES",_("プロパティを表示"))
		self.RegisterMenuCommand(self.hFileMenu,"FILE_MKDIR",_("新規ディレクトリ作成"))
		self.RegisterMenuCommand(self.hFileMenu,"FILE_FILEOPTEST",_("テスト中のファイルオペレーションを実行"))
		self.RegisterMenuCommand(self.hFileMenu,"FILE_EXIT",_("終了"))

		#編集メニューの中身
		self.RegisterMenuCommand(self.hEditMenu,"EDIT_COPY",_("コピー"))
		self.RegisterMenuCommand(self.hEditMenu,"EDIT_CUT",_("切り取り"))
		self.RegisterMenuCommand(self.hEditMenu,"EDIT_NAMECOPY",_("名前をコピー"))
		self.RegisterMenuCommand(self.hEditMenu,"EDIT_FULLPATHCOPY",_("フルパスをコピー"))
		self.RegisterMenuCommand(self.hEditMenu,"EDIT_SELECTALL",_("全て選択"))
		self.RegisterMenuCommand(self.hEditMenu,"EDIT_SORTNEXT",_("次の並び順"))
		self.RegisterMenuCommand(self.hEditMenu,"EDIT_SEARCH",_("検索"))
		self.RegisterMenuCommand(self.hEditMenu,"EDIT_UPDATEFILELIST",_("最新の情報に更新"))
		self.RegisterMenuCommand(self.hEditMenu,"EDIT_SORTSELECT",_("並び順を選択"))
		self.RegisterMenuCommand(self.hEditMenu,"EDIT_SORTCYCLEAD",_("昇順/降順切り替え"))
		self.RegisterMenuCommand(self.hEditMenu,"EDIT_OPENCONTEXTMENU",_("コンテキストメニューを開く"))

		#移動メニューの中身
		self.RegisterMenuCommand(self.hMoveMenu,"MOVE_FORWARD",_("開く"))
		self.RegisterMenuCommand(self.hMoveMenu,"MOVE_FORWARD_ADMIN",_("管理者として開く"))
		self.RegisterMenuCommand(self.hMoveMenu,"MOVE_FORWARD_TAB",_("別のタブで開く"))
		self.RegisterMenuCommand(self.hMoveMenu,"MOVE_FORWARD_STREAM",_("開く(ストリーム)"))
		self.RegisterMenuCommand(self.hMoveMenu,"MOVE_BACKWARD",_("上の階層へ"))
		self.RegisterMenuCommand(self.hMoveMenu,"MOVE_CLOSECURRENTTAB",_("現在のタブを閉じる"))
		self.RegisterMenuCommand(self.hMoveMenu,"MOVE_TOPFILE",_("先頭ファイルへ"))
		self.RegisterMenuCommand(self.hMoveMenu,"MOVE_MARKSET",_("表示中の場所をマーク"))
		self.RegisterMenuCommand(self.hMoveMenu,"MOVE_MARK",_("マークした場所へ移動"))

		for m in globalVars.app.userCommandManagers:
			subMenu=wx.Menu()
			for v in m.paramMap:
				self.RegisterMenuCommand(subMenu,m.refHead+v,v)
				if m==globalVars.app.openHereCommand:
					tabs.base.FalconTabBase.selectItemMenuConditions[0].append(m.refHead+v)
					tabs.base.FalconTabBase.selectItemMenuConditions[2].append(m.refHead+v)
					tabs.base.FalconTabBase.selectItemTypeMenuConditions[browsableObjects.File].append(m.refHead+v)
					tabs.streamList.blockMenuList.append(m.refHead+v)
			self.hMoveMenu.AppendSubMenu(subMenu,globalVars.app.userCommandManagers[m])

		self.RegisterMenuCommand(self.hMoveMenu,"MOVE_MARK",_("マークした場所へ移動"))

		#読みメニューの中身
		subMenu=wx.Menu()
		self.RegisterMenuCommand(subMenu,"READ_CONTENT_PREVIEW",_("ファイルをプレビュー"))
		self.RegisterMenuCommand(subMenu,"READ_CONTENT_READHEADER",_("テキストヘッダー読み"))
		self.RegisterMenuCommand(subMenu,"READ_CONTENT_READFOOTER",_("テキストフッター読み"))
		self.hReadMenu.AppendSubMenu(subMenu,_("プレビュー"))
		self.RegisterMenuCommand(self.hReadMenu,"READ_FILEINFO",_("ファイル情報"))
		self.RegisterMenuCommand(self.hReadMenu,"READ_DRIVEINFO",_("ドライブ情報"))
		self.RegisterMenuCommand(self.hReadMenu,"READ_CURRENTFOLDER",_("現在のフォルダ名を読み上げ"))
		self.RegisterMenuCommand(self.hReadMenu,"READ_FOLDERFILENUMBER",_("フォルダ数とファイル数を読み上げ"))
		self.RegisterMenuCommand(self.hReadMenu,"READ_LISTINFO",_("一覧情報を読み上げ"))
		self.RegisterMenuCommand(self.hReadMenu,"READ_SETMOVEMENTREAD",_("移動先の読み方を設定"))

		#ツールメニューの中身
		self.RegisterMenuCommand(self.hToolMenu,"TOOL_DIRCALC",_("フォルダ容量計算"))
		self.RegisterMenuCommand(self.hToolMenu,"TOOL_HASHCALC",_("ファイルハッシュの計算"))
		self.RegisterMenuCommand(self.hToolMenu,"TOOL_ADDPATH",_("環境変数PATHに追加"))
		self.RegisterMenuCommand(self.hToolMenu,"TOOL_EJECT_DRIVE",_("ドライブの取り外し"))
		self.RegisterMenuCommand(self.hToolMenu,"TOOL_EJECT_DEVICE",_("デバイスの取り外し"))


		#環境メニューの中身
		self.RegisterMenuCommand(self.hEnvMenu,"ENV_TESTDIALOG",_("テストダイアログを表示"))
		self.RegisterMenuCommand(self.hEnvMenu,"ENV_FONTTEST",_("フォントテストダイアログを表示"))
		#ヘルプメニューの中身
		self.RegisterMenuCommand(self.hHelpMenu,"HELP_VERINFO",_("バージョン情報"))

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

		#イベントとショートカットキーの登録
		target.Bind(wx.EVT_MENU,event.OnMenuSelect)
		self.ApplyShortcut(target)

		#名前の変更中に出しておくダミーのメニューバー
		#これがないとメニューバーの高さ分リストオブジェクトの大きさが変わってしまうために必要
		self.hDisableMenuBar=wx.MenuBar()
		self.hDisableSubMenu=wx.Menu()
		self.hDisableMenuBar.Append(self.hDisableSubMenu,_("現在メニューは操作できません"))

class Events(BaseEvents):
	def OnMenuSelect(self,event):
		"""メニュー項目が選択されたときのイベントハンドら。"""
		#ショートカットキーが無効状態のときは何もしない
		if not self.parent.SetShortcutEnable:
			event.Skip()
			return

		selected=event.GetId()#メニュー識別しの数値が出る

		#選択された(ショートカットで押された)メニューが無効状態なら何もしない
		if self.parent.menu.blockCount[selected]>0:
			event.Skip()
			return

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
		if selected==menuItemsStore.getRef("MOVE_FORWARD_TAB"):
			self.OpenNewTab()
			return
		if selected==menuItemsStore.getRef("MOVE_CLOSECURRENTTAB"):
			self.CloseTab()
			return
		if selected==menuItemsStore.getRef("EDIT_COPY"):
			self.parent.activeTab.Copy()
			return
		if selected==menuItemsStore.getRef("EDIT_CUT"):
			self.parent.activeTab.Cut()
			return
		if selected==menuItemsStore.getRef("EDIT_NAMECOPY"):
			self.parent.activeTab.NameCopy()
			return
		if selected==menuItemsStore.getRef("EDIT_FULLPATHCOPY"):
			self.parent.activeTab.FullpathCopy()
			return
		if selected==menuItemsStore.getRef("EDIT_SELECTALL"):
			self.parent.activeTab.SelectAll()
			return
		if selected==menuItemsStore.getRef("MOVE_TOPFILE"):
			self.parent.activeTab.GoToTopFile()
			return
		if selected==menuItemsStore.getRef("MOVE_MARKSET"):
			self.parent.activeTab.MarkSet()
			self.parent.menu.hMenuBar.Enable(menuItemsStore.getRef("MOVE_MARK"),True)
			return
		if selected==menuItemsStore.getRef("MOVE_MARK"):
			self.parent.activeTab.GoToMark()
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
		if selected==menuItemsStore.getRef("EDIT_SEARCH"):
			self.Search()
			return
		if selected==menuItemsStore.getRef("EDIT_UPDATEFILELIST"):
			self.UpdateFilelist()
			return
		if selected==menuItemsStore.getRef("EDIT_OPENCONTEXTMENU"):
			self.OpenContextMenu()
			return
		if selected==menuItemsStore.getRef("FILE_MAKESHORTCUT"):
			target=self.parent.activeTab.GetSelectedItems().GetElement(0)		#browsableObjects
			d=views.makeShortcut.Dialog(target.basename)
			d.Initialize()
			ret=d.Show()
			if ret==wx.ID_CANCEL: return
			self.parent.activeTab.MakeShortcut(d.GetValue())
			d.Destroy()
			return
		if selected==menuItemsStore.getRef("FILE_CHANGEATTRIBUTE"):
			d=views.changeAttribute.Dialog()
			d.Initialize()
			ret=d.Show()
			if ret==wx.ID_CANCEL: return
			val=d.GetValue()
			d.Destroy()
			self.parent.activeTab.ChangeAttribute(val)
			return
		if selected==menuItemsStore.getRef("FILE_MKDIR"):
			d=views.mkdir.Dialog()
			d.Initialize()
			ret=d.Show()
			if ret==wx.ID_CANCEL: return
			self.parent.activeTab.MakeDirectory(d.GetValue())
			d.Destroy()
			return
		if selected==menuItemsStore.getRef("FILE_FILEOPTEST"):
			self.parent.activeTab.FileOperationTest()
			return
		if selected==menuItemsStore.getRef("FILE_TRASH"):
			self.parent.activeTab.Trash()
			return
		if selected==menuItemsStore.getRef("FILE_DELETE"):
			self.parent.activeTab.Delete()
			return
		if selected==menuItemsStore.getRef("FILE_VIEW_DETAIL"):
			elem=self.parent.activeTab.listObject.GetElement(self.parent.activeTab.GetFocusedItem())
			dic={}
			dic[_("名前")]=elem.basename
			dic[_("パス")]=elem.fullpath
			if elem.__class__==browsableObjects.File or elem.__class__==browsableObjects.Stream:
				dic[_("サイズ")]=misc.ConvertBytesTo(elem.size,misc.UNIT_AUTO,True)
				dic[_("サイズ(バイト)")]=elem.size
			if elem.__class__==browsableObjects.File:
				dic[_("作成日時")]=elem.creationDate.strftime("%Y/%m/%d(%a) %H:%M:%S")
				dic[_("更新日時")]=elem.modDate.strftime("%Y/%m/%d(%a) %H:%M:%S")
				dic[_("属性")]=elem.longAttributesString
				dic[_("種類")]=elem.typeString
				if not elem.shortName=="":
					dic[_("短い名前")]=elem.shortName
				else:
					dic[_("短い名前")]=_("なし")
			if elem.__class__==browsableObjects.Folder:
				if elem.size>=0:
					dic[_("サイズ")]=misc.ConvertBytesTo(elem.size,misc.UNIT_AUTO,True)
					dic[_("サイズ(バイト)")]=elem.size
				else:
					size=misc.GetDirectorySize(elem.fullpath)
					if size>=0:
						dic[_("サイズ")]=misc.ConvertBytesTo(size,misc.UNIT_AUTO,True)
						dic[_("サイズ(バイト)")]=size
					else:
						dic[_("サイズ")]=_("不明")
						dic[_("サイズ(バイト)")]=_("不明")
				dic[_("作成日時")]=elem.creationDate.strftime("%Y/%m/%d(%a) %H:%M:%S")
				dic[_("更新日時")]=elem.modDate.strftime("%Y/%m/%d(%a) %H:%M:%S")
				dic[_("属性")]=elem.longAttributesString
				dic[_("種類")]=elem.typeString
				if not elem.shortName=="":
					dic[_("短い名前")]=elem.shortName
				else:
					dic[_("短い名前")]=_("なし")
			if elem.__class__==browsableObjects.Drive:
				if elem.free>=0:
					dic[_("フォーマット")]=fileSystemManager.GetFileSystemObject(elem.letter)
					dic[_("空き容量")]=misc.ConvertBytesTo(elem.free, misc.UNIT_AUTO,True)
				else:
					dic[_("フォーマット")]=_("未挿入")
				if elem.total>0:
					dic[_("空き容量")]+=" ("+str(elem.free*100//elem.total)+"%)"
				if elem.free>=0:
					dic[_("総容量")]=misc.ConvertBytesTo(elem.total, misc.UNIT_AUTO, True)
				dic[_("種類")]=elem.typeString
			d=views.objectDetail.Dialog()
			d.Initialize(dic)
			d.Show()
			d.Destroy()
			return
		if selected==menuItemsStore.getRef("FILE_SHOWPROPERTIES"):
			self.parent.activeTab.ShowProperties()
			return
		if selected==menuItemsStore.getRef("READ_CURRENTFOLDER"):
			self.parent.activeTab.ReadCurrentFolder()
			return
		if selected==menuItemsStore.getRef("READ_CONTENT_PREVIEW"):
			self.parent.activeTab.PlaySound()
			return
		if selected==menuItemsStore.getRef("TOOL_DIRCALC"):
			self.parent.activeTab.DirCalc()
			return
		if selected==menuItemsStore.getRef("TOOL_HASHCALC"):
			d=views.makeHash.Dialog(self.parent.activeTab.GetFocusedElement().fullpath)
			d.Initialize()
			d.Show()
			d.Destroy()
			return
		if selected==menuItemsStore.getRef("TOOL_ADDPATH"):
			t=self.parent.activeTab.GetSelectedItems()
			if item in t:
				if item.__class__!=browsableObjects.Folder:
					return
			t=t.GetItemPaths()
			if misc.addPath(t):
				dialog(_("パスの追加"),_("ユーザ環境変数PATHに追加しました。"))
			else:
				dialog(_("パスの追加"),_("追加に失敗しました。"))
			return
		if selected==menuItemsStore.getRef("TOOL_EJECT_DRIVE"):
			ret=deviceCtrl.ejectDrive(self.parent.activeTab.GetFocusedElement().letter)
			if ret==errorCodes.OK:
				dialog(_("成功"),_("ドライブは安全に切断されました。"))
				self.UpdateFilelist(False)
			elif ret==errorCodes.FILE_NOT_FOUND:
				dialog(_("エラー"),_("指定されたドライブが見つかりません。既に取り外しされた可能性があります。"))
			elif ret==errorCodes.UNKNOWN:
				#エラー表示はむこうでやってる
				pass
			elif errorCodes.ACCESS_DENIED:
				dialog(_("エラー"),_("取り外しに失敗しました。")+_("このドライブは使用中の可能性があります。"))
			return
		if selected==menuItemsStore.getRef("TOOL_EJECT_DEVICE"):
			if self.parent.activeTab.GetFocusedItem()<0:
				return
			ret=deviceCtrl.EjectDevice(self.parent.activeTab.GetFocusedElement().letter)
			if ret==errorCodes.OK:
				dialog(_("成功"),_("デバイスは安全に取り外せる状態になりました。"))
				self.UpdateFilelist(False)
			elif ret==errorCodes.UNKNOWN:
				dialog(_("エラー"),_("デバイスの取り外しに失敗しました。"))
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

		for m in globalVars.app.userCommandManagers:
			if m.isRefHit(selected):
				if m == globalVars.app.favoriteDirectory:
					ret=self.parent.activeTab.Move(m.get(selected))
					if issubclass(ret.__class__,tabs.base.FalconTabBase): self.parent.ReplaceCurrentTab(ret)
					#TODO: エラー処理する
				else:
					path=m.get(selected)
					path=path.replace("%1",self.parent.activeTab.listObject.rootDirectory)
					prm=re.sub(r"^[^ ]* (.*)$",r"\1",path)
					path=re.sub(r"^([^ ]*).*$",r"\1",path)
					self.parent.activeTab.RunFile(path,False,prm)
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
		ret=p.activeTab.GoBackward()
		if issubclass(ret.__class__,tabs.base.FalconTabBase): p.ReplaceCurrentTab(ret)
		if ret==errorCodes.NOT_SUPPORTED:
			dialog(_("エラー"),_("このオペレーションはサポートされていません。"))
		elif ret==errorCodes.BOUNDARY:
			globalVars.app.PlaySound(globalVars.app.config["sounds"]["boundary"])

	def OpenNewTab(self):
		"""選択中のディレクトリを新しいタブで開く"""
		e=self.parent.activeTab.GetFocusedElement()
		self.parent.Navigate(e.fullpath,as_new_tab=True)

	def CloseTab(self):
		self.parent.CloseTab(self.parent.activeTab)

	def Search(self):
		basePath=self.parent.activeTab.listObject.rootDirectory
		out_lst=[]#入力画面が出てるときに、もうファイルリスト取得を開始してしまう
		task=workerThreads.RegisterTask(workerThreadTasks.GetRecursiveFileList,{'path': basePath, 'out_lst': out_lst,'eol':True})
		d=views.search.Dialog(basePath)
		d.Initialize()
		ret=d.Show()
		if ret==wx.ID_CANCEL:
			task.Cancel()
			return
		#end 途中でやめた
		val=d.GetValue()
		d.Destroy()
		target={'action': 'search', 'basePath': basePath, 'out_lst': out_lst, 'keyword': val['keyword']}
		self.parent.Navigate(target,as_new_tab=True)

	def GoForward(self,stream=False,admin=False):
		"""forward アクションを実行。stream=True で、ファイルを開く代わりにストリームを開く。admin=True で、管理者モード。"""
		p=self.parent
		st=True if stream else False
		ret=p.activeTab.GoForward(st,admin)
		if issubclass(ret.__class__,tabs.base.FalconTabBase): p.ReplaceCurrentTab(ret)
		if ret==errorCodes.NOT_SUPPORTED:
			dialog(_("エラー"),_("このオペレーションはサポートされていません。"))
		elif ret==errorCodes.BOUNDARY:
			dialog("test","mada")

	def SortNext(self):
		"""sortNext アクションを実行。"""
		p=self.parent
		ret=p.activeTab.SortNext()
		if ret==errorCodes.NOT_SUPPORTED:
			dialog(_("エラー"),_("このオペレーションはサポートされていません。"))

	def SortSelect(self):
		"""並び順を指定する。"""
		t=self.parent.activeTab
		t.SortSelect()

	def SortCycleAd(self):
		t=self.parent.activeTab
		t.SortCycleAd()

	def UpdateFilelist(self,silence=True):
		ret=self.parent.activeTab.UpdateFilelist(silence=silence)

	def OpenContextMenu(self,silence=True):
		self.parent.activeTab.OpenContextMenu(event=None)
