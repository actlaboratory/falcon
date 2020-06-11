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
import views.registOriginalAssociation
import views.execProgram

import workerThreads
import workerThreadTasks

from logging import getLogger, FileHandler, Formatter
from simpleDialog import dialog
from .base import *

from simpleDialog import *

EVENT_FROM_SELF=-1	#適当な数字。そのイベントは自分自身で投げたものであることを示している


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
			self.app.config.getint(self.identifier,"sizeX",800,400),
			self.app.config.getint(self.identifier,"sizeY",600,300),
			self.app.config.getint(self.identifier,"positionX",50,0),
			self.app.config.getint(self.identifier,"positionY",50,0)
		)
		self.menu=Menu()
		self.menu.InitShortcut(self.identifier)

		#お気に入りフォルダと「ここで開く」のショートカットキーを登録
		for target in (globalVars.app.userCommandManagers):
			for v in target.keyMap:
				if target==globalVars.app.openHereCommand:
					tabs.base.FalconTabBase.selectItemMenuConditions[0].append(target.refHead+v)
					tabs.base.FalconTabBase.selectItemMenuConditions[2].append(target.refHead+v)
					tabs.base.FalconTabBase.selectItemTypeMenuConditions[browsableObjects.File].append(target.refHead+v)
					tabs.base.FalconTabBase.selectItemTypeMenuConditions[browsableObjects.NetworkResource].append(target.refHead+v)
					tabs.streamList.StreamListTab.blockMenuList.append(target.refHead+v)
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
		self.hFrame.Bind(wx.EVT_CLOSE, self.OnClose)
		self.hFrame.Show()
		self.app.SetTopWindow(self.hFrame)
		self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
		return True

	def OnClose(self,event=None):
		"""ウィンドウが閉じられる直前に呼ばれる。"""
		if not event.CanVeto():#強制シャットダウン
			self.hFrame.Destroy()
			return
		#end 強制終了
		num=self.GetNumberOfTabs()
		if num>1:
			dlg=wx.MessageDialog(self.hFrame,_("%(tabs)d個のタブが開いています。これらのタブを全て閉じて、Falconを終了してもよろしいですか？") % {'tabs': num},_("終了確認"),wx.YES_NO|wx.ICON_QUESTION)
			ret=dlg.ShowModal()
			if ret==wx.ID_NO:
				event.Veto()
				return
			#end no
		#end 複数タブが開いている渓谷
		self.hFrame.Destroy()

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
		self.activeTab.hListCtrl.SetFocus()
	#end makeFirstTab

	def Navigate(self,target,as_new_tab=False):
		"""指定のパスにナビゲートする。"""
		if isinstance(target,dict):
			self.log.debug("Creating new tab %s..." % target['action'])
		else:
			self.log.debug("Creating new tab %s..." % target)
		#end log
		s=_("新しいタブ") if len(self.tabs)>0 else _("falcon")
		globalVars.app.say(s)
		hPanel=views.ViewCreator.makePanel(self.hTabCtrl)
		creator=views.ViewCreator.ViewCreator(1,hPanel,None)
		newtab=tabs.navigator.Navigate(target,create_new_tab_info=(self,creator))
		newtab.hListCtrl.SetAcceleratorTable(self.menu.acceleratorTable)
		self.tabs.append(newtab)
		#self.hTabCtrl.InsertPage(len(self.tabs)-1,hPanel,"tab%d" % (len(self.tabs)),False)
		self.hTabCtrl.InsertPage(len(self.tabs)-1,hPanel,newtab.GetTabName(),False)

		self.ActivateTab(len(self.tabs)-1)

	def ReplaceCurrentTab(self,newtab):
		"""現在のタブのインスタンスを入れ替える。ファイルリストからドライブリストになったときなどに使う。"""
		i=self.GetTabIndex(self.activeTab)

		#environmentの内容を引き継ぐ
		newtab.SetEnvironment(self.activeTab.environment)

		self.UpdateMenuState(self.activeTab,newtab)
		self.tabs[i]=newtab
		self.activeTab.OnBeforeChangeTab()
		self.activeTab.OnClose()
		self.activeTab=newtab

		#タブ名変更。activeTab書き換え後に呼ぶ必要がある
		self.UpdateTabName()
	#end ReplaceCurrentTab

	def ActivateTab(self,pageNo):
		"""指定されたインデックスのタブをアクティブにする。"""

		self.UpdateMenuState(self.activeTab,self.tabs[pageNo])
		self.activeTab=self.tabs[pageNo]
		self.hTabCtrl.SetSelection(pageNo)

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
		popped_tab.OnClose()
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

	def GetNumberOfTabs(self):
		return len(self.tabs)

	def GetTabIndex(self,target):
		"""targetで指定されたtabObjectがtabsの中でインデックス何番か取得"""
		i=0
		for elem in self.tabs:
			if elem is target: return i
			i+=1
		return -1

	def ChangeTab(self,event):
		"""タブ変更イベント"""
		self.activeTab.OnBeforeChangeTab()
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

	def UpdateMenuState(self,old,new):
		#メニューのブロック状態を変更
		if old:
			self.menu.UnBlock(old.blockMenuList)
		self.menu.Block(new.blockMenuList)
		self.menu.Enable(menuItemsStore.getRef("MOVE_MARK"),new.IsMarked())
		self.menu.Enable(menuItemsStore.getRef("EDIT_UNMARKITEM_ALL"),new.hasCheckedItem())
		new.ItemSelected()		#メニューのブロック情報を選択中アイテム数の状況に合わせるために必用

	def UpdateTabName(self):
		"""タブ名変更の可能性があるときにtabsからたたかれる"""
		index=self.GetTabIndex(self.activeTab)
		if index>=0:
			self.hTabCtrl.SetPageText(index,self.activeTab.GetTabName())


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
		self.RegisterMenuCommand(self.hFileMenu,{
			"FILE_RENAME":_("名前を変更"),
			"FILE_CHANGEATTRIBUTE":_("属性を変更"),
			"FILE_MAKESHORTCUT":_("ショートカットを作成"),
			"FILE_TRASH":_("ゴミ箱へ移動"),
			"FILE_DELETE":_("完全削除"),
			"FILE_VIEW_DETAIL":_("詳細情報を表示"),
			"FILE_SHOWPROPERTIES":_("プロパティを表示"),
			"FILE_MKDIR":_("新規ディレクトリ作成"),
			"FILE_FILEOPTEST":_("テスト中のファイルオペレーションを実行"),
			"FILE_EXIT":_("終了")
		})

		#編集メニューの中身
		self.RegisterMenuCommand(self.hEditMenu,{
			"EDIT_COPY":_("コピー"),
			"EDIT_CUT":_("切り取り"),
			"EDIT_PAST":_("貼り付け"),
			"EDIT_NAMECOPY":_("名前をコピー"),
			"EDIT_FULLPATHCOPY":_("フルパスをコピー"),
			"EDIT_SELECTALL":_("全て選択"),
			"EDIT_SEARCH":_("検索"),
			"EDIT_UPDATEFILELIST":_("最新の情報に更新"),
			"EDIT_MARKITEM":_("チェック／チェック解除"),
			"EDIT_MARKITEM_ALL":_("すべてチェック"),
			"EDIT_UNMARKITEM_ALL":_("すべてチェック解除"),
			"EDIT_MARKITEM_INVERSE":_("チェック状態反転"),
			"EDIT_OPENCONTEXTMENU":_("コンテキストメニューを開く"),
		})

		#移動メニューの中身
		self.RegisterMenuCommand(self.hMoveMenu,{
			"MOVE_FORWARD":_("開く"),
			"MOVE_FORWARD_ADMIN":_("管理者として開く"),
			"MOVE_EXEC_ORIGINAL_ASSOCIATION":_("独自関連付けで実行"),
			"MOVE_FORWARD_TAB":_("別のタブで開く"),
			"MOVE_FORWARD_STREAM":_("開く(ストリーム)"),
			"MOVE_BACKWARD":_("上の階層へ"),
			"MOVE_NEWTAB":_("新しいタブ"),
			"MOVE_CLOSECURRENTTAB":_("現在のタブを閉じる"),
			"MOVE_TOPFILE":_("先頭ファイルへ"),
			"MOVE_SPECIAL_UP":_("上にジャンプ"),
			"MOVE_SPECIAL_DOWN":_("下にジャンプ"),
			"MOVE_MARKSET":_("表示中の場所をマーク"),
			"MOVE_MARK":_("マークした場所へ移動")
		})

		for m in globalVars.app.userCommandManagers:
			subMenu=wx.Menu()
			for v in m.paramMap:
				self.RegisterMenuCommand(subMenu,m.refHead+v,v)
			self.hMoveMenu.AppendSubMenu(subMenu,globalVars.app.userCommandManagers[m])

		#読みメニューの中身
		subMenu=wx.Menu()
		self.RegisterMenuCommand(subMenu,{
			"READ_CONTENT_PREVIEW":_("ファイルをプレビュー"),
			"READ_CONTENT_READHEADER":_("テキストヘッダー読み"),
			"READ_CONTENT_READFOOTER":_("テキストフッター読み")
		}),
		self.RegisterMenuCommand(self.hReadMenu,"READ_PREVIEW",_("プレビュー"),subMenu)
		self.RegisterMenuCommand(self.hReadMenu,{
			"READ_CURRENTFOLDER":_("現在のフォルダ名を読み上げ"),
			"READ_LISTITEMNUMBER":_("リスト項目数を読み上げ"),
			"READ_LISTINFO":_("一覧情報を読み上げ"),
			"READ_SETMOVEMENTREAD":_("移動先の読み方を設定")
		})

		#ツールメニューの中身
		self.RegisterMenuCommand(self.hToolMenu,{
			"TOOL_DIRCALC":_("フォルダ容量計算"),
			"TOOL_HASHCALC":_("ファイルハッシュの計算"),
			"TOOL_EXEC_PROGRAM":_("ファイル名を指定して実行"),
			"TOOL_ADDPATH":_("環境変数PATHに追加"),
			"TOOL_EJECT_DRIVE":_("ドライブの取り外し"),
			"TOOL_EJECT_DEVICE":_("デバイスの取り外し"),
		})

		#表示メニューの中身
		self.RegisterMenuCommand(self.hViewMenu,{
			"VIEW_SORTNEXT":_("次の並び順"),
			"VIEW_SORTSELECT":_("並び順を選択"),
			"VIEW_SORTCYCLEAD":_("昇順/降順切り替え"),
			"VIEW_DRIVE_INFO":_("ドライブ情報の表示"),
		})
		subMenu=wx.Menu()
		self.RegisterMenuCommand(self.hViewMenu,"VIEW_SORT_COLUMN",_("カラムの並び替え"),subMenu)

		#環境メニューの中身
		self.RegisterMenuCommand(self.hEnvMenu,{
			"ENV_REGIST_ORIGINAL_ASSOCIATION":_("独自関連付けの管理"),
			"ENV_TESTDIALOG":_("テストダイアログを表示"),
			"ENV_FONTTEST":_("フォントテストダイアログを表示")
		})

		#ヘルプメニューの中身
		self.RegisterMenuCommand(self.hHelpMenu,{
			"HELP_VERINFO":_("バージョン情報")
		})

		#メニューバー
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
		target.Bind(wx.EVT_MENU_OPEN,event.OnMenuOpen)
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

		#カラムソートは特別対応
		if selected>=constants.MENU_ID_SORT_COLUMN:
			self.ColumnSort(selected)
			return

		#キー重複対応のためのIDの場合には、イベントを投げ直す
		#複数投げられるが、有効状態の者は１つだけなはず
		if globalVars.app.hMainView.menu.keymap.isRefHit(selected):
			for ref in globalVars.app.hMainView.menu.keymap.GetOriginalRefs(selected):
				newEvent=wx.CommandEvent(event.GetEventType(),ref)
				newEvent.SetExtraLong(EVENT_FROM_SELF)		#キー操作無効を示す音を鳴らさない
				wx.PostEvent(globalVars.app.hMainView.hFrame.GetEventHandler(),newEvent)
			return

		#選択された(ショートカットで押された)メニューが無効状態なら何もしない
		if self.parent.menu.blockCount[selected]>0:
			if not event.GetExtraLong()==EVENT_FROM_SELF:
				globalVars.app.PlaySound(globalVars.app.config["sounds"]["boundary"])
			event.Skip()
			return

		if selected==menuItemsStore.getRef("MOVE_BACKWARD"):
			self.GoBackward()
			return
		if selected==menuItemsStore.getRef("MOVE_FORWARD"):
			self.GoForward(False)
			return
		if selected==menuItemsStore.getRef("MOVE_EXEC_ORIGINAL_ASSOCIATION"):
			elem=self.parent.activeTab.GetFocusedElement()
			if (not isinstance(elem,browsableObjects.Folder)) and isinstance(elem,(browsableObjects.File,browsableObjects.Stream,browsableObjects.GrepItem)):
				extention=os.path.splitext(elem.fullpath)[1][1:].lower()
				if extention in globalVars.app.config["originalAssociation"]:
					config=globalVars.app.config["originalAssociation"][extention]
				else:
					config=globalVars.app.config["originalAssociation"]["<default_file>"]
			else:
				config=globalVars.app.config["originalAssociation"]["<default_dir>"]
			misc.RunFile(config,prm=elem.fullpath)
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
		if selected==menuItemsStore.getRef("MOVE_NEWTAB"):
			self.NewTab()
			return
		if selected==menuItemsStore.getRef("EDIT_COPY"):
			self.parent.activeTab.Copy()
			return
		if selected==menuItemsStore.getRef("EDIT_CUT"):
			self.parent.activeTab.Cut()
			return
		if selected==menuItemsStore.getRef("EDIT_PAST"):
			self.parent.activeTab.Past()
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
		if selected==menuItemsStore.getRef("MOVE_SPECIAL_UP"):
			self.parent.activeTab.Jump(constants.ARROW_UP)
			return
		if selected==menuItemsStore.getRef("MOVE_SPECIAL_DOWN"):
			self.parent.activeTab.Jump(constants.ARROW_DOWN)
			return
		if selected==menuItemsStore.getRef("MOVE_MARKSET"):
			self.parent.activeTab.MarkSet()
			self.parent.menu.Enable(menuItemsStore.getRef("MOVE_MARK"),True)
			return
		if selected==menuItemsStore.getRef("MOVE_MARK"):
			self.parent.activeTab.GoToMark()
			return
		if selected==menuItemsStore.getRef("VIEW_SORTNEXT"):
			self.DelaiedCall(self.SortNext)
			return
		if selected==menuItemsStore.getRef("EDIT_MARKITEM"):
			self.parent.activeTab.OnSpaceKey()
			return
		if selected==menuItemsStore.getRef("EDIT_MARKITEM_ALL"):
			self.parent.activeTab.CheckAll()
			return
		if selected==menuItemsStore.getRef("EDIT_UNMARKITEM_ALL"):
			self.parent.activeTab.UncheckAll()
			return
		if selected==menuItemsStore.getRef("EDIT_MARKITEM_INVERSE"):
			self.parent.activeTab.CheckInverse()
			return
		if selected==menuItemsStore.getRef("VIEW_SORTSELECT"):
			self.SortSelect()
			return
		if selected==menuItemsStore.getRef("VIEW_SORTCYCLEAD"):
			self.DelaiedCall(self.SortCycleAd)
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
			elem=self.parent.activeTab.GetFocusedElement()
			self.ShowDetail(elem)
			return
		if selected==menuItemsStore.getRef("FILE_SHOWPROPERTIES"):
			self.parent.activeTab.ShowProperties()
			return
		if selected==menuItemsStore.getRef("READ_CURRENTFOLDER"):
			self.DelaiedCall(self.parent.activeTab.ReadCurrentFolder)
			return
		if selected==menuItemsStore.getRef("READ_LISTITEMNUMBER"):
			self.DelaiedCall(self.parent.activeTab.ReadListItemNumber)
			return
		if selected==menuItemsStore.getRef("READ_LISTINFO"):
			self.DelaiedCall(self.parent.activeTab.ReadListInfo)
			return
		if selected==menuItemsStore.getRef("READ_CONTENT_PREVIEW"):
			self.parent.activeTab.Preview()
			return
		if selected==menuItemsStore.getRef("READ_CONTENT_READHEADER"):
			self.DelaiedCall(self.parent.activeTab.ReadHeader)
			return
		if selected==menuItemsStore.getRef("READ_CONTENT_READFOOTER"):
			self.DelaiedCall(self.parent.activeTab.ReadFooter)
			return
		if selected==menuItemsStore.getRef("READ_SETMOVEMENTREAD"):
			self.parent.activeTab.SetMovementRead()
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
		if selected==menuItemsStore.getRef("TOOL_EXEC_PROGRAM"):
			self.ExecProgram()
			return
		if selected==menuItemsStore.getRef("TOOL_ADDPATH"):
			t=self.parent.activeTab.GetSelectedItems()
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
			ret=deviceCtrl.EjectDevice(self.parent.activeTab.GetFocusedElement().letter)
			if ret==errorCodes.OK:
				dialog(_("成功"),_("デバイスは安全に取り外せる状態になりました。"))
				self.UpdateFilelist(False)
			elif ret==errorCodes.UNKNOWN:
				dialog(_("エラー"),_("デバイスの取り外しに失敗しました。"))
			return
		if selected==menuItemsStore.getRef("VIEW_DRIVE_INFO"):
			rootPath=self.parent.activeTab.listObject.rootDirectory[0]
			elem=None
			if len(rootPath)==1:
				elem=lists.drive.GetDriveObject(int(ord(rootPath)-65))
			else:	#ネットワークリソース
				lst=lists.drive.DriveList()
				lst.Initialize(None,True)
				for d in lst:
					if d.basename==rootPath:
						elem=d
			if elem==None:
				dialog(_("エラー"),_("ドライブ情報の取得に失敗しました。"))
				return
			self.ShowDetail(elem)
			return
		if selected==menuItemsStore.getRef("ENV_REGIST_ORIGINAL_ASSOCIATION"):
			config=globalVars.app.config["originalAssociation"]
			d=views.registOriginalAssociation.Dialog(dict(config.items()))
			d.Initialize()
			if d.Show()==wx.ID_CANCEL:
				d.Destroy()
				return
			result={}
			result["originalAssociation"]=d.GetValue()
			globalVars.app.config.remove_section("originalAssociation")
			globalVars.app.config.read_dict(result)
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
					misc.RunFile(path,False,prm)
				return

		dialog(_("エラー"),_("操作が定義されていないメニューです。"))
		return

	def OnMenuOpen(self,event):
		#カラムソートメニューの場合のみ
		if event.GetMenu()==self.parent.menu.hMenuBar.FindItemById(menuItemsStore.getRef("VIEW_SORT_COLUMN")).GetSubMenu():
			menu=self.parent.menu.hMenuBar.FindItemById(menuItemsStore.getRef("VIEW_SORT_COLUMN")).GetSubMenu()
			#一旦全て削除
			for i in range(menu.GetMenuItemCount()):
				menu.DestroyItem(menu.FindItemByPosition(0))

			#カラム数分登録
			i=0
			for title in self.parent.activeTab.GetListColumns():
				subMenu=wx.Menu()
				subMenu.Append(constants.MENU_ID_SORT_COLUMN+2*i,"前へ")
				subMenu.Append(constants.MENU_ID_SORT_COLUMN+2*i+1,"後ろへ")
				menu.AppendSubMenu(subMenu,title)
				i+=1
			menu.Enable(constants.MENU_ID_SORT_COLUMN,False)
			menu.Enable(constants.MENU_ID_SORT_COLUMN+2*(i-1)+1,False)
		event.Skip()

	def ColumnSort(self,menuId):
		order=self.parent.activeTab.GetColumnOrderList()
		if menuId%2==0:	#前へ
			target=int((menuId-constants.MENU_ID_SORT_COLUMN)/2)
			tmp=order[target]
			order[target]=order[target-1]
			order[target-1]=tmp
		else:	#後ろへ
			target=int((menuId-constants.MENU_ID_SORT_COLUMN-1)/2)
			tmp=order[target]
			order[target]=order[target+1]
			order[target+1]=tmp
		self.parent.activeTab.SetColumnOrderList(order)

	def StartRename(self):
		"""リネームを開始する。"""
		self.parent.activeTab.StartRename()
	#end StartRename

	def DelaiedCall(self,callable):
		"""メニューから、すぐに何かを読み上げる機能を実行すると、メニューが閉じてリストに戻った読み上げにかき消されてしまう。なので、エンターが押されているかどうかを判定して、その場合にcallableの実行時間を遅らせる。"""
		if not wx.GetKeyState(wx.WXK_RETURN):
			callable()
			return
		else:
			later=wx.CallLater(200,callable)
	#end delaiedCall

	def ShowVersionInfo(self):
		"""バージョン情報を表示する。"""
		dialog(_("バージョン情報"),_("%(app)s Version %(ver)s.\nCopyright (C) %(year)s %(names)s") % {"app":constants.APP_NAME, "ver":constants.APP_VERSION, "year":constants.APP_COPYRIGHT_YEAR, "names":constants.APP_DEVELOPERS})


	def ExecProgram(self):
		d=views.execProgram.Dialog()
		d.Initialize()
		if d.Show()==wx.ID_CANCEL:return
		val=d.GetValue()
		d.Destroy()
		self.parent.activeTab.ExecProgram(val)

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

	def NewTab(self):
		if os.path.isdir(os.path.expandvars(globalVars.app.config["browse"]["startPath"])):
			self.parent.Navigate(os.path.expandvars(globalVars.app.config["browse"]["startPath"]),as_new_tab=True)
		else:
			self.parent.Navigate("",as_new_tab=True)

	def Search(self):
		basePath=self.parent.activeTab.listObject.rootDirectory
		out_lst=[]#入力画面が出てるときに、もうファイルリスト取得を開始してしまう
		task=workerThreads.RegisterTask(workerThreadTasks.GetRecursiveFileList,{'path': basePath, 'out_lst': out_lst,'eol':True})
		d=views.search.Dialog(basePath)
		d.Initialize()
		canceled=False
		while(True):
			ret=d.Show()
			if ret==wx.ID_CANCEL:
				task.Cancel()
				canceled=True
				break
			#end キャンセルして抜ける
			val=d.GetValue()
			if val['isRegularExpression']:
				ret=misc.ValidateRegularExpression(val['keyword'])
				if ret!="OK":
					dialog(_("エラー"), _("正規表現の文法が間違っています。\nエラー内容: %(error)s") % {'error': ret})
					continue
				#end 正規表現違う
			#end 正規表現モードがオンかどうか
			break
		#end 入力が正しくなるまで
		d.Destroy()
		if canceled: return
		actionstr="search" if val['type']==0 else "grep"
		target={'action': actionstr, 'basePath': basePath, 'out_lst': out_lst, 'keyword': val['keyword'], 'isRegularExpression': val['isRegularExpression']}
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

	def UpdateFilelist(self,silence=False):
		ret=self.parent.activeTab.UpdateFilelist(silence=silence)

	def OpenContextMenu(self,silence=True):
		self.parent.activeTab.OpenContextMenu(event=None)

	def ShowDetail(self,elem):
		dic={}
		dic[_("名前")]=elem.basename
		dic[_("パス")]=elem.fullpath
		if isinstance(elem,browsableObjects.Folder):
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
		elif isinstance(elem,browsableObjects.File) or type(elem)==browsableObjects.Stream:
			dic[_("サイズ")]=misc.ConvertBytesTo(elem.size,misc.UNIT_AUTO,True)
			dic[_("サイズ(バイト)")]=elem.size
		if isinstance(elem,browsableObjects.File):
			dic[_("作成日時")]=elem.creationDate.strftime("%Y/%m/%d(%a) %H:%M:%S")
			dic[_("更新日時")]=elem.modDate.strftime("%Y/%m/%d(%a) %H:%M:%S")
			dic[_("属性")]=elem.longAttributesString
			dic[_("種類")]=elem.typeString
			if not elem.shortName=="":
				dic[_("短い名前")]=elem.shortName
			else:
				dic[_("短い名前")]=_("なし")
		if type(elem)==browsableObjects.Drive:
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
		if type(elem)==browsableObjects.NetworkResource:
			dic[_("IPアドレス")]=elem.address
		d=views.objectDetail.Dialog()
		d.Initialize(dic)
		d.Show()
		d.Destroy()
		return
