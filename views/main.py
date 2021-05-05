# -*- coding: utf-8 -*-
# Falcon app main view
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import copy
import history
import logging
import os
import pickle
import sys
import wx
import win32file
import re
import ctypes
import pywintypes

import browsableObjects
import misc
import constants
import errorCodes
import ConfigManager
import globalVars
import lists
import tabs.navigator
import menuItemsStore
import fileSystemManager
import deviceCtrl

import views.changeAttribute
import views.favoriteDirectory
import views.fonttest
import views.globalKeyConfig
import views.SympleImputDialog
import views.makeHash
import views.makeShortcut
import views.objectDetail
import views.openHere
import views.search
import views.registerOriginalAssociation

import workerThreads
import workerThreadTasks

from logging import getLogger, FileHandler, Formatter
from simpleDialog import dialog
from .base import *

from simpleDialog import *

EVENT_FROM_SELF = -1  # 適当な数字。そのイベントは自分自身で投げたものであることを示している


class View(BaseView):
    def Initialize(self):
        t = misc.Timer()
        self.log.debug("created")
        self.events = Events(self, self.identifier)
        title = ""
        if(ctypes.windll.shell32.IsUserAnAdmin()):
            title += "[" + _("管理者") + "]"
        title += constants.APP_NAME
        super().Initialize(
            title,
            self.app.config.getint(self.identifier, "sizeX", 800, 400),
            self.app.config.getint(self.identifier, "sizeY", 600, 300),
            self.app.config.getint(self.identifier, "positionX", 50, 0),
            self.app.config.getint(self.identifier, "positionY", 50, 0)
        )
        self.menu = Menu(self.identifier)
        self.AddUserCommandKey()
        self.InstallMenuEvent(self.menu, self.events.OnMenuSelect)
        self.AddUserCommandMenu()

        self.tabs = []
        self.activeTab = None  # 最初なので空
        self.hTabCtrl = self.creator.tabCtrl(
            _("タブ選択"), self.ChangeTab, 0, wx.EXPAND, 1)
        self.MakeFirstTab()
        self.activeTab.hListCtrl.SetFocus()
        self.hFrame.Bind(wx.EVT_CLOSE, self.OnClose)
        self.hFrame.Bind(wx.EVT_MENU_OPEN, self.events.OnMenuOpen)
        if self.app.config.getboolean(self.identifier, "maximized", False):
            self.hFrame.Maximize()
        self.hFrame.Show()
        self.app.SetTopWindow(self.hFrame)
        self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
        return True

    def OnClose(self, event=None):
        """ウィンドウが閉じられる直前に呼ばれる。"""
        self.log.info("received close event(force=" +
                      ("true" if not event.CanVeto() else "false") + ")")
        if not event.CanVeto():  # 強制シャットダウン
            self.hFrame.Destroy()
            return
        # end 強制終了
        num = self.GetNumberOfTabs()
        if num > 1:
            dlg = wx.MessageDialog(
                self.hFrame,
                _("%(tabs)d個のタブが開いています。これらのタブを全て閉じて、Falconを終了してもよろしいですか？") % {
                    'tabs': num},
                _("終了確認"),
                wx.YES_NO | wx.ICON_QUESTION)
            ret = dlg.ShowModal()
            if ret == wx.ID_NO:
                event.Veto()
                self.log.info("CloseEvent.Veto(). user select cancel.")
                return
            # end no
        # end 複数タブが開いている渓谷
        event.Skip()

    def MakeFirstTab(self):
        """最初のタブを作成する。"""

        if len(sys.argv) > 1:
            result = self.Navigate(
                misc.analyzeUserInputPath(
                    sys.argv[1],
                    os.getcwd()),
                as_new_tab=True)
            if result == errorCodes.OK:
                return
            else:
                dialog(
                    "Error",
                    _("引数で指定されたディレクトリ '%(dir)s' は存在しません。") % {
                        "dir": sys.argv[1]})
        if self.app.config["browse"]["startPath"] != "":
            result = self.Navigate(
                misc.analyzeUserInputPath(
                    self.app.config["browse"]["startPath"],
                    os.getcwd()),
                as_new_tab=True)
        else:  # ドライブ一覧を表示
            result = self.Navigate("", as_new_tab=True)
        if result == errorCodes.OK:
            return
        else:
            if os.path.abspath(
                os.path.expandvars(
                    self.app.config["browse"]["startPath"])) != "":
                dialog("Error", _("設定された起動時ディレクトリ '%(dir)s' は存在しません。") %
                       {"dir": self.app.config["browse"]["startPath"]})
            result = self.Navigate("", as_new_tab=True)
        if result == errorCodes.OK:
            return
        else:
            dialog(
                "Error",
                _("ドライブ一覧の読み込みに失敗しました。大変お手数ですが、ログファイルを添付して開発者までお問い合わせください。"))
    # end makeFirstTab

    def Navigate(self, target, as_new_tab=False):
        """指定のパスにナビゲートする。"""
        if isinstance(target, dict):
            self.log.debug("Creating new tab %s..." % target['action'])
        else:
            self.log.debug("Creating new tab %s..." % target)
        # end log
        wx.CallLater(200, self._sayNewTab)
        hPanel = views.ViewCreator.makePanel(self.hTabCtrl)
        creator = views.ViewCreator.ViewCreator(1, hPanel, None)
        newtab = tabs.navigator.Navigate(
            target, create_new_tab_info=(self, creator))
        if isinstance(newtab, int):  # Error
            return newtab
        self.tabs.append(newtab)
        #self.hTabCtrl.InsertPage(len(self.tabs)-1,hPanel,"tab%d" % (len(self.tabs)),False)
        self.hTabCtrl.InsertPage(len(self.tabs) -
                                 1, hPanel, newtab.GetTabName(), False)

        self.ActivateTab(len(self.tabs) - 1)
        return errorCodes.OK

    def _sayNewTab(self):
        s = _("新しいタブ") if len(self.tabs) > 1 else _("falcon")
        globalVars.app.say(s, interrupt=True)

    def ReplaceCurrentTab(self, newtab):
        """現在のタブのインスタンスを入れ替える。ファイルリストからドライブリストになったときなどに使う。"""
        i = self.GetTabIndex(self.activeTab)
        if i == -1:
            return  # 最初のタブの作成

        self.UpdateMenuState(self.activeTab, newtab)
        self.tabs[i] = newtab
        self.activeTab.OnBeforeChangeTab()
        self.activeTab.OnClose()
        self.activeTab = newtab
        self.menu.ApplyShortcut(self.activeTab.hListCtrl)

        # タブ名変更。activeTab書き換え後に呼ぶ必要がある
        self.UpdateTabName()
    # end ReplaceCurrentTab

    def ActivateTab(self, pageNo, triggerOnReactivate=False):
        """指定されたインデックスのタブをアクティブにする。"""
        self.UpdateMenuState(self.activeTab, self.tabs[pageNo])
        self.activeTab = self.tabs[pageNo]
        self.hTabCtrl.SetSelection(pageNo)
        self.menu.ApplyShortcut(self.activeTab.hListCtrl)
        if triggerOnReactivate:
            self.activeTab.onReactivate()

    def CloseTab(self, pageNo):
        """指定されたインデックスのタブを閉じる。閉じたタブがアクティブだった場合は、別のタブをアクティブ状態にする。全てのタブが閉じられた場合は、終了イベントを投げる。"""
        if not isinstance(pageNo, int):  # 数字じゃなくてタブオブジェクトが渡ってた
            found = -1
            for i in range(len(self.tabs)):
                if self.tabs[i] is pageNo:
                    found = i
                    break
                # end if
            # end for
            if found == -1:
                return
            pageNo = found
        # end ページ番号じゃなかったときの検索

        active_tab = self.activeTab
        popped_tab = self.tabs.pop(pageNo)
        popped_tab.OnClose()
        if len(self.tabs) == 0:  # タブがなくなった
            self.hFrame.Close()
            return
        # タブがなくなったらソフト終了
        # この時点で、 noteBook がリストコントロールをデリートするらしいので、他の場所で明示的に消してはいけないとリファレンスに書いてある
        self.hTabCtrl.DeletePage(pageNo)
        self.hTabCtrl.SendSizeEvent()
        if active_tab is popped_tab:  # アクティブなタブを閉じた
            print("popped tab")
            new_pageNo = pageNo
            if new_pageNo >= len(self.tabs):
                new_pageNo = len(self.tabs) - 1
            print("trigger")
            self.ActivateTab(new_pageNo, triggerOnReactivate=True)
        # end アクティブタブを閉じた場合に後ろのタブを持って来る
    # end closeTab

    def GetNumberOfTabs(self):
        return len(self.tabs)

    def GetTabIndex(self, target):
        """targetで指定されたtabObjectがtabsの中でインデックス何番か取得"""
        i = 0
        for elem in self.tabs:
            if elem is target:
                return i
            i += 1
        return -1

    def ChangeTab(self, event):
        """タブ変更イベント"""
        self.activeTab.OnBeforeChangeTab()
        pageNo = event.GetSelection()
        self.ActivateTab(pageNo)

    def SetShortcutEnabled(self, en):
        super().SetShortcutEnabled(en)
        if en:
            # 通常のメニューバーに戻す
            self.hFrame.SetMenuBar(self.menu.hMenuBar)
        else:
            # 名前の変更中にはダミーのメニューバーを出しておく
            # これがないとメニューバーの高さ分リストオブジェクトの大きさが変わってしまうために必要
            self.hFrame.SetMenuBar(self.menu.hDisableMenuBar)
        # SetMenuBarの後に呼び出しが必要
        self.creator.GetSizer().Layout()

    def UpdateMenuState(self, old, new):
        # メニューのブロック状態を変更
        self.menu.Enable(menuItemsStore.getRef("MOVE_MARK"), new.IsMarked())
        self.menu.Enable(menuItemsStore.getRef("EDIT_UNMARKITEM_ALL"), new.hasCheckedItem())
        self.menu.Enable(menuItemsStore.getRef("EDIT_MARKITEM_ALL"), len(new.checkedItem) != len(new.listObject))
        self.menu.Enable(menuItemsStore.getRef("MOVE_HIST_NEXT"), new.environment["history"].hasNext())
        self.menu.Enable(menuItemsStore.getRef("MOVE_HIST_PREV"), new.environment["history"].hasPrevious())

    def UpdateTabName(self):
        """タブ名変更の可能性があるときにtabsからたたかれる"""
        index = self.GetTabIndex(self.activeTab)
        if index >= 0:
            self.hTabCtrl.SetPageText(index, self.activeTab.GetTabName())

    def AddUserCommandKey(self):
        # お気に入りフォルダと「ここで開く」のショートカットキーを登録
        for target in (globalVars.app.userCommandManagers):
            for v in target.keyMap:
                if target.keyMap[v] != "":  # キーが指定されていない場合は無視
                    self.menu.keymap.add(
                        self.identifier, target.refHead + v, target.keyMap[v])
        errors = self.menu.keymap.GetError(self.identifier)
        if errors:
            tmp = _(
                "お気に入りディレクトリもしくは「ここで開く」で設定されたショートカットキーが正しくありません。キーが重複しているか、存在しないキー名を指定しています。以下のキーの設定内容をご確認ください。\n\n")
            for v in errors:
                tmp += v + "\n"
            dialog(_("エラー"), tmp)

    def AddUserCommandMenu(self):
        for m in globalVars.app.userCommandManagers:
            # 既に登録済みならインデックスを取得していったん削除する
            item = self.menu.hMoveMenu.FindItemById(
                menuItemsStore.getRef(m.refHead))
            if item:
                index = self.menu.hMoveMenu.GetMenuItems().index(item)
                self.menu.hMoveMenu.DestroyItem(item)
            else:
                index = self.menu.hMoveMenu.GetMenuItemCount()

            subMenu = wx.Menu()
            for v in m.paramMap:
                self.menu.RegisterMenuCommand(subMenu, m.refHead + v, v)

            if m == globalVars.app.favoriteDirectory:
                self.menu.RegisterMenuCommand(subMenu, (
                    "",
                    "MOVE_ADD_FAVORITE",
                    "MOVE_SETTING_FAVORITE"
                ))
            else:
                self.menu.RegisterMenuCommand(subMenu, (
                    "",
                    "MOVE_SETTING_OPEN_HERE"
                ))
            title = globalVars.app.userCommandManagers[m]
            self.menu.RegisterMenuCommand(
                self.menu.hMoveMenu, m.refHead, title, subMenu, index)
            self.hFrame.SetMenuBar(self.menu.hMenuBar)

    def UpdateUserCommand(self):
        self.menu.InitShortcut()  # キーマップを再取得
        self.AddUserCommandKey()  # ユーザコマンドを登録
        self.menu.ApplyShortcut(
            self.activeTab.hListCtrl)  # acceleratorTable再取得
        self.AddUserCommandMenu()  # メニューバーの登録更新
        return

    def GetKeyEntries(self):
        return self.menu.keymap.GetEntries(self.identifier)

    def PopupMenu(self, hMenu):
        self.hFrame.PopupMenu(hMenu)

    def SetShortcutEnabled(self, en):
        """
                ショートカットキーの有効/無効を切り替える。
                AcceleratorTableとメニューバーのそれぞれに登録されているので、両方の対策が必要。
        """
        # 登録先が違うのでsuperのものを使わない
        if hasattr(self, "activeTab"):
            return self._SetShortcutEnabled(en, self.activeTab.hListCtrl)


class Menu(BaseMenu):
    def __init__(self, identifier):
        filter = keyFilter = keymap.KeyFilter().SetDefault(False, True)
        filter.AddFunctionKey(
            ("LEFTARROW",
             "RIGHTARROW",
             "NUMPAD_DIVIDE",
             "NUMPAD_MULTIPLY"))

        super().__init__(identifier, keyFilter=filter)

        # これ以降はユーザ設定の追加なのでフィルタを変更
        filter = keyFilter = keymap.KeyFilter().SetDefault(False, True)
        filter.AddFunctionKey(
            ("LEFTARROW",
             "RIGHTARROW",
             "NUMPAD_DIVIDE",
             "NUMPAD_MULTIPLY"))
        self.keymap.filter = filter

    def Apply(self, target):
        """指定されたウィンドウに、メニューを適用する。"""

        # メニューの大項目を作る
        self.hFileMenu = wx.Menu()
        self.hEditMenu = wx.Menu()
        self.hMoveMenu = wx.Menu()
        self.hReadMenu = wx.Menu()
        self.hToolMenu = wx.Menu()
        self.hViewMenu = wx.Menu()
        self.hEnvMenu = wx.Menu()
        self.hHelpMenu = wx.Menu()

        # ファイルメニューの中身
        self.RegisterMenuCommand(self.hFileMenu, (
            "FILE_RENAME",
            "FILE_CHANGEATTRIBUTE",
            "FILE_MAKESHORTCUT",
            "FILE_TRASH",
            "FILE_DELETE",
            "FILE_VIEW_DETAIL",
            "FILE_SHOWPROPERTIES",
            "FILE_MKDIR",
            "FILE_FILEOPTEST",
            "FILE_EXIT"
        ))

        # 編集メニューの中身
        self.RegisterMenuCommand(self.hEditMenu, (
            "EDIT_COPY",
            "EDIT_CUT",
            "EDIT_PAST",
            "EDIT_NAMECOPY",
            "EDIT_FULLPATHCOPY",
            "EDIT_SELECTALL",
            "EDIT_SEARCH",
            "EDIT_UPDATEFILELIST",
            "EDIT_MARKITEM",
            "EDIT_MARKITEM_ALL",
            "EDIT_UNMARKITEM_ALL",
            "EDIT_MARKITEM_INVERSE",
            "EDIT_OPENCONTEXTMENU",
        ))

        # 移動メニューの中身
        self.RegisterMenuCommand(self.hMoveMenu, (
            "MOVE_FORWARD",
            "MOVE_FORWARD_ADMIN",
            "MOVE_EXEC_ORIGINAL_ASSOCIATION",
            "MOVE_FORWARD_TAB",
            "MOVE_FORWARD_STREAM",
            "MOVE_BACKWARD",
            "MOVE_NEWTAB",
            "MOVE_CLOSECURRENTTAB",
            "MOVE_TOPFILE",
            "MOVE_SPECIAL_UP",
            "MOVE_SPECIAL_DOWN",
            "MOVE_HIST_NEXT",
            "MOVE_HIST_PREV",
            "MOVE_MARKSET",
            "MOVE_MARK",
            "MOVE_INPUT_DIR"
        ))

        # 読みメニューの中身
        subMenu = wx.Menu()
        self.RegisterMenuCommand(subMenu, (
            "READ_CONTENT_PREVIEW",
            "READ_CONTENT_READHEADER",
            "READ_CONTENT_READFOOTER"
        )),
        self.RegisterMenuCommand(
            self.hReadMenu,
            "READ_PREVIEW",
            _("プレビュー"),
            subMenu)
        self.RegisterMenuCommand(self.hReadMenu, (
            "READ_CURRENTFOLDER",
            "READ_LISTITEMNUMBER",
            "READ_LISTINFO",
            "READ_SETMOVEMENTREAD"
        ))

        # ツールメニューの中身
        self.RegisterMenuCommand(self.hToolMenu, (
            "TOOL_DIRCALC",
            "TOOL_HASHCALC",
            "TOOL_EXEC_PROGRAM",
            "TOOL_ADDPATH",
            "TOOL_EJECT_DRIVE",
            "TOOL_EJECT_DEVICE",
        ))

        # 表示メニューの中身
        self.RegisterMenuCommand(self.hViewMenu, (
            "VIEW_SORTNEXT",
            "VIEW_SORTSELECT",
            "VIEW_SORTCYCLEAD",
            "VIEW_DRIVE_INFO",
        ))
        subMenu = wx.Menu()
        self.RegisterMenuCommand(
            self.hViewMenu,
            "VIEW_SORT_COLUMN",
            _("カラムの並び替え"),
            subMenu)

        # 環境メニューの中身
        self.RegisterMenuCommand(self.hEnvMenu, (
            "ENV_REGIST_ORIGINAL_ASSOCIATION",
            "ENV_KEY_CONFIG",
            "ENV_TESTDIALOG",
            "ENV_PASTTABTEST",
            "ENV_FONTTEST"
        ))

        # ヘルプメニューの中身
        self.RegisterMenuCommand(self.hHelpMenu, (
            "HELP_VERINFO"
        ))

        # メニューバー
        self.hMenuBar.Append(self.hFileMenu, _("ファイル"))
        self.hMenuBar.Append(self.hEditMenu, _("編集"))
        self.hMenuBar.Append(self.hMoveMenu, _("移動"))
        self.hMenuBar.Append(self.hReadMenu, _("読み"))
        self.hMenuBar.Append(self.hToolMenu, _("ツール"))
        self.hMenuBar.Append(self.hViewMenu, _("表示"))
        self.hMenuBar.Append(self.hEnvMenu, _("環境"))
        self.hMenuBar.Append(self.hHelpMenu, _("ヘルプ"))
        target.SetMenuBar(self.hMenuBar)

        self.ApplyShortcut()


class Events(BaseEvents):
    def OnMenuSelect(self, event):
        """メニュー項目が選択されたときのイベントハンドら。"""
        # ショートカットキーが無効状態のときは何もしない
        if not self.parent.shortcutEnable:
            event.Skip()
            return

        # プレビュー再生停止等のため、キー押下をタブへ通知
        # ここにきている場合KeyDownイベントはとれないため
        self.parent.activeTab.OnKeyDown()

        selected = event.GetId()  # メニュー識別しの数値が出る

        # カラムソートは特別対応
        if selected >= constants.MENU_ID_SORT_COLUMN:
            self.ColumnSort(selected)
            return

        # キー重複対応のためのIDの場合には、イベントを投げ直す
        # 複数投げられるが、有効状態の者は１つだけなはず
        if globalVars.app.hMainView.menu.keymap.isRefHit(selected):
            for ref in globalVars.app.hMainView.menu.keymap.GetOriginalRefs(
                    selected):
                newEvent = wx.CommandEvent(event.GetEventType(), ref)
                newEvent.SetExtraLong(EVENT_FROM_SELF)  # キー操作無効を示す音を鳴らさない
                wx.PostEvent(
                    globalVars.app.hMainView.hFrame.GetEventHandler(),
                    newEvent)
            return

        # 選択された(ショートカットで押された)メニューが無効状態なら何もしない
        if selected in views.menuBlocker.testMenu(self.parent.activeTab):
            if not event.GetExtraLong() == EVENT_FROM_SELF:
                globalVars.app.PlaySound(globalVars.app.config["sounds"]["boundary"])
            event.Skip()
            return

        if selected == menuItemsStore.getRef("ENV_PASTTABTEST"):
            self.parent.Navigate({"action": "past"}, as_new_tab=True)
            return
        # end test
        if selected == menuItemsStore.getRef("MOVE_BACKWARD"):
            self.GoBackward()
            return
        if selected == menuItemsStore.getRef("MOVE_FORWARD"):
            self.GoForward(False)
            return
        if selected == menuItemsStore.getRef("MOVE_EXEC_ORIGINAL_ASSOCIATION"):
            elem = self.parent.activeTab.GetFocusedElement()
            if (not isinstance(elem, browsableObjects.Folder)) and isinstance(
                    elem, (browsableObjects.File, browsableObjects.Stream, browsableObjects.GrepItem)):
                extention = os.path.splitext(elem.fullpath)[1][1:].lower()
                if extention in globalVars.app.config["originalAssociation"]:
                    config = globalVars.app.config["originalAssociation"][extention]
                else:
                    config = globalVars.app.config["originalAssociation"]["<default_file>"]
            else:
                config = globalVars.app.config["originalAssociation"]["<default_dir>"]
            config = misc.analyzeUserInputPath(config)
            misc.RunFile(config, prm="\"%s\"" % (elem.fullpath))
            return
        if selected == menuItemsStore.getRef("ENV_KEY_CONFIG"):
            keys = self.parent.menu.keymap.map[self.parent.identifier.upper()]
            keyData = {}
            menuData = {}
            for refName in defaultKeymap.defaultKeymap["MainView".upper()].keys(
            ):
                title = menuItemsDic.dic[refName]
                if refName in keys:
                    keyData[title] = keys[refName]
                else:
                    keyData[title] = "なし"
                menuData[title] = refName
            d = views.globalKeyConfig.Dialog(keyData, menuData)
            d.Initialize()
            if d.Show() == wx.ID_CANCEL:
                return

            result = {}
            keyData, menuData = d.GetValue()

            # キーマップの既存設定を置き換える
            keymap = ConfigManager.ConfigManager()
            keymap.read(constants.KEYMAP_FILE_NAME)
            for name, key in keyData.items():
                if key != _("なし"):
                    keymap[self.parent.identifier.upper()][menuData[name]] = key
                else:
                    keymap[self.parent.identifier.upper()][menuData[name]] = ""
            keymap.write()

            # ショートカットキーの変更適用とメニューバーの再描画
            self.parent.UpdateUserCommand()
            self.parent.menu.Apply(self.parent.hFrame)
            return
        if selected == menuItemsStore.getRef("MOVE_FORWARD_ADMIN"):
            self.GoForward(False, admin=True)
            return
        if selected == menuItemsStore.getRef("MOVE_FORWARD_STREAM"):
            self.GoForward(True)
            return
        if selected == menuItemsStore.getRef("MOVE_FORWARD_TAB"):
            self.OpenNewTab()
            return
        if selected == menuItemsStore.getRef("MOVE_CLOSECURRENTTAB"):
            self.CloseTab()
            return
        if selected == menuItemsStore.getRef("MOVE_NEWTAB"):
            self.NewTab()
            return
        if selected == menuItemsStore.getRef("EDIT_COPY"):
            self.parent.activeTab.Copy()
            return
        if selected == menuItemsStore.getRef("EDIT_CUT"):
            self.parent.activeTab.Cut()
            return
        if selected == menuItemsStore.getRef("EDIT_PAST"):
            self.parent.activeTab.Past()
            return
        if selected == menuItemsStore.getRef("EDIT_NAMECOPY"):
            self.parent.activeTab.NameCopy()
            return
        if selected == menuItemsStore.getRef("EDIT_FULLPATHCOPY"):
            self.parent.activeTab.FullpathCopy()
            return
        if selected == menuItemsStore.getRef("EDIT_SELECTALL"):
            self.parent.activeTab.SelectAll()
            return
        if selected == menuItemsStore.getRef("MOVE_TOPFILE"):
            self.parent.activeTab.GoToTopFile()
            return
        if selected == menuItemsStore.getRef("MOVE_SPECIAL_UP"):
            self.parent.activeTab.Jump(constants.ARROW_UP)
            return
        if selected == menuItemsStore.getRef("MOVE_SPECIAL_DOWN"):
            self.parent.activeTab.Jump(constants.ARROW_DOWN)
            return
        if selected == menuItemsStore.getRef("MOVE_HIST_PREV"):
            self.parent.activeTab.GoHistPrevious()
            return
        if selected == menuItemsStore.getRef("MOVE_HIST_NEXT"):
            self.parent.activeTab.GoHistNext()
            return
        if selected == menuItemsStore.getRef("MOVE_MARKSET"):
            self.parent.activeTab.MarkSet()
            self.parent.menu.Enable(menuItemsStore.getRef("MOVE_MARK"), True)
            return
        if selected == menuItemsStore.getRef("MOVE_MARK"):
            self.parent.activeTab.GoToMark()
            return
        if selected == menuItemsStore.getRef("MOVE_INPUT_DIR"):
            d = views.SympleImputDialog.Dialog(_("パスを指定して移動"), _("移動先"))
            d.Initialize()
            if d.Show() == wx.ID_CANCEL:
                return
            self.parent.activeTab.Move(
                misc.analyzeUserInputPath(
                    d.GetValue(),
                    self.parent.activeTab.listObject.rootDirectory))
            return
        if selected == menuItemsStore.getRef("MOVE_ADD_FAVORITE"):
            d = views.favoriteDirectory.SettingDialog(
                self.parent.hFrame,
                os.path.basename(
                    self.parent.activeTab.listObject.rootDirectory),
                self.parent.activeTab.listObject.rootDirectory,
                "")
            d.Initialize()
            ret = d.Show()
            if ret == wx.ID_CANCEL:
                return
            name, path, key = d.GetValue()

            if name in globalVars.app.favoriteDirectory:
                dlg = wx.MessageDialog(
                    self.parent.hFrame,
                    _("この名前は既に登録されています。登録を上書きしますか？"),
                    _("上書き確認"),
                    wx.YES_NO | wx.ICON_QUESTION)
                if dlg.ShowModal() == wx.ID_NO:
                    return
            v = dict(globalVars.app.favoriteDirectory.keyMap.items())
            v[name] = key
            if not views.KeyValueSettingDialogBase.KeySettingValidation(
                    dict(globalVars.app.favoriteDirectory.keyMap.items()), v, None):
                return

            globalVars.app.favoriteDirectory.add(name, path, key)
            self.parent.UpdateUserCommand()
            return
        if selected == menuItemsStore.getRef("MOVE_SETTING_FAVORITE"):
            d = views.favoriteDirectory.Dialog(
                dict(
                    globalVars.app.favoriteDirectory.paramMap.items()), dict(
                    globalVars.app.favoriteDirectory.keyMap.items()))
            d.Initialize()
            ret = d.Show()
            if ret == wx.ID_CANCEL:
                return

            result = {}
            params, keys = d.GetValue()
            globalVars.app.favoriteDirectory.replace(params, keys)
            self.parent.UpdateUserCommand()
            return
        if selected == menuItemsStore.getRef("MOVE_SETTING_OPEN_HERE"):
            d = views.openHere.Dialog(
                dict(
                    globalVars.app.openHereCommand.paramMap.items()), dict(
                    globalVars.app.openHereCommand.keyMap.items()))
            d.Initialize()
            ret = d.Show()
            if ret == wx.ID_CANCEL:
                return

            result = {}
            params, keys = d.GetValue()
            globalVars.app.openHereCommand.replace(params, keys)
            self.parent.UpdateUserCommand()
            return
        if selected == menuItemsStore.getRef("VIEW_SORTNEXT"):
            self.DelaiedCall(self.SortNext)
            return
        if selected == menuItemsStore.getRef("EDIT_MARKITEM"):
            self.parent.activeTab.OnSpaceKey()
            return
        if selected == menuItemsStore.getRef("EDIT_MARKITEM_ALL"):
            self.parent.activeTab.CheckAll()
            return
        if selected == menuItemsStore.getRef("EDIT_UNMARKITEM_ALL"):
            self.parent.activeTab.UncheckAll()
            return
        if selected == menuItemsStore.getRef("EDIT_MARKITEM_INVERSE"):
            self.parent.activeTab.CheckInverse()
            return
        if selected == menuItemsStore.getRef("VIEW_SORTSELECT"):
            self.SortSelect()
            return
        if selected == menuItemsStore.getRef("VIEW_SORTCYCLEAD"):
            self.DelaiedCall(self.SortCycleAd)
            return
        if selected == menuItemsStore.getRef("EDIT_SEARCH"):
            self.Search()
            return
        if selected == menuItemsStore.getRef("EDIT_UPDATEFILELIST"):
            self.UpdateFilelist()
            return
        if selected == menuItemsStore.getRef("EDIT_OPENCONTEXTMENU"):
            self.OpenContextMenu()
            return
        if selected == menuItemsStore.getRef("FILE_MAKESHORTCUT"):
            target = self.parent.activeTab.GetSelectedItems().GetElement(0)  # browsableObjects
            d = views.makeShortcut.Dialog(
                target.basename,
                target.canLnkTarget,
                target.canHardLinkTarget,
                target.canSynLinkTarget)
            d.Initialize()
            ret = d.Show()
            if ret == wx.ID_CANCEL:
                return
            self.parent.activeTab.MakeShortcut(d.GetValue())
            return
        if selected == menuItemsStore.getRef("FILE_CHANGEATTRIBUTE"):
            d = views.changeAttribute.Dialog(
                self.parent.activeTab.GetSelectedItems().GetAttributeCheckState())
            d.Initialize()
            ret = d.Show()
            if ret == wx.ID_CANCEL:
                return
            val = d.GetValue()
            self.parent.activeTab.ChangeAttribute(val)
            return
        if selected == menuItemsStore.getRef("FILE_MKDIR"):
            d = views.SympleImputDialog.Dialog(_("ディレクトリ作成"), _("ディレクトリ名"))
            d.Initialize()
            if d.Show() == wx.ID_CANCEL:
                return
            self.parent.activeTab.MakeDirectory(d.GetValue())
            return
        if selected == menuItemsStore.getRef("FILE_FILEOPTEST"):
            self.parent.activeTab.FileOperationTest()
            return
        if selected == menuItemsStore.getRef("FILE_TRASH"):
            self.parent.activeTab.Trash()
            return
        if selected == menuItemsStore.getRef("FILE_DELETE"):
            self.parent.activeTab.Delete()
            return
        if selected == menuItemsStore.getRef("FILE_VIEW_DETAIL"):
            elem = self.parent.activeTab.GetFocusedElement()
            self.ShowDetail(elem)
            return
        if selected == menuItemsStore.getRef("FILE_SHOWPROPERTIES"):
            self.parent.activeTab.ShowProperties()
            return
        if selected == menuItemsStore.getRef("READ_CURRENTFOLDER"):
            self.DelaiedCall(self.parent.activeTab.ReadCurrentFolder)
            return
        if selected == menuItemsStore.getRef("READ_LISTITEMNUMBER"):
            self.DelaiedCall(self.parent.activeTab.ReadListItemNumber)
            return
        if selected == menuItemsStore.getRef("READ_LISTINFO"):
            self.DelaiedCall(self.parent.activeTab.ReadListInfo)
            return
        if selected == menuItemsStore.getRef("READ_CONTENT_PREVIEW"):
            self.parent.activeTab.Preview()
            return
        if selected == menuItemsStore.getRef("READ_CONTENT_READHEADER"):
            self.DelaiedCall(self.parent.activeTab.ReadHeader)
            return
        if selected == menuItemsStore.getRef("READ_CONTENT_READFOOTER"):
            self.DelaiedCall(self.parent.activeTab.ReadFooter)
            return
        if selected == menuItemsStore.getRef("READ_SETMOVEMENTREAD"):
            self.parent.activeTab.SetMovementRead()
            return
        if selected == menuItemsStore.getRef("TOOL_DIRCALC"):
            self.parent.activeTab.DirCalc()
            return
        if selected == menuItemsStore.getRef("TOOL_HASHCALC"):
            d = views.makeHash.Dialog(
                self.parent.activeTab.GetFocusedElement().fullpath)
            d.Initialize()
            d.Show()
            return
        if selected == menuItemsStore.getRef("TOOL_EXEC_PROGRAM"):
            self.ExecProgram()
            return
        if selected == menuItemsStore.getRef("TOOL_ADDPATH"):
            t = self.parent.activeTab.GetSelectedItems()
            t = t.GetItemPaths()
            if misc.addPath(t):
                dialog(_("パスの追加"), _("ユーザ環境変数PATHに追加しました。"))
            else:
                dialog(_("パスの追加"), _("追加に失敗しました。"))
            return
        if selected == menuItemsStore.getRef("TOOL_EJECT_DRIVE"):
            ret = deviceCtrl.ejectDrive(
                self.parent.activeTab.GetFocusedElement().letter)
            if ret == errorCodes.OK:
                dialog(_("成功"), _("ドライブは安全に切断されました。"))
                self.UpdateFilelist(False)
            elif ret == errorCodes.FILE_NOT_FOUND:
                dialog(_("エラー"), _("指定されたドライブが見つかりません。既に取り外しされた可能性があります。"))
            elif ret == errorCodes.UNKNOWN:
                # エラー表示はむこうでやってる
                pass
            elif errorCodes.ACCESS_DENIED:
                dialog(_("エラー"), _("取り外しに失敗しました。") + _("このドライブは使用中の可能性があります。"))
            return
        if selected == menuItemsStore.getRef("TOOL_EJECT_DEVICE"):
            ret = deviceCtrl.EjectDevice(
                self.parent.activeTab.GetFocusedElement().letter)
            if ret == errorCodes.OK:
                dialog(_("成功"), _("デバイスは安全に取り外せる状態になりました。"))
                self.UpdateFilelist(False)
            elif ret == errorCodes.UNKNOWN:
                dialog(_("エラー"), _("デバイスの取り外しに失敗しました。"))
            return
        if selected == menuItemsStore.getRef("VIEW_DRIVE_INFO"):
            elem = self.parent.activeTab.GetRootObject()
            if elem is None:
                dialog(_("エラー"), _("ドライブ情報の取得に失敗しました。"))
                return
            self.ShowDetail(elem)
            return
        if selected == menuItemsStore.getRef(
                "ENV_REGIST_ORIGINAL_ASSOCIATION"):
            config = globalVars.app.config["originalAssociation"]
            d = views.registerOriginalAssociation.Dialog(dict(config.items()))
            d.Initialize()
            if d.Show() == wx.ID_CANCEL:
                return
            result = {}
            result["originalAssociation"] = d.GetValue()[0]
            globalVars.app.config.remove_section("originalAssociation")
            globalVars.app.config.read_dict(result)
            return
        if selected == menuItemsStore.getRef("ENV_TESTDIALOG"):
            return
        if selected == menuItemsStore.getRef("ENV_FONTTEST"):
            self.fonttest = views.fonttest.View()
            self.fonttest.Initialize()
            return
        if selected == menuItemsStore.getRef("FILE_RENAME"):
            self.StartRename()
            return
        if selected == menuItemsStore.getRef("FILE_EXIT"):
            self.parent.hFrame.Close()
            return
        if selected == menuItemsStore.getRef("HELP_VERINFO"):
            self.ShowVersionInfo()
            return

        for m in globalVars.app.userCommandManagers:
            if m.isRefHit(selected):
                if m == globalVars.app.favoriteDirectory:
                    ret = self.parent.activeTab.Move(misc.analyzeUserInputPath(
                        m.get(selected), self.parent.activeTab.listObject.rootDirectory))
                    #TODO: エラー処理する
                else:  # ここで開く
                    path = m.get(selected)
                    path, prm = misc.PathParamSplit(path)
                    prm = prm.replace(
                        "%1", self.parent.activeTab.listObject.rootDirectory)
                    misc.RunFile(path, False, prm)
                return

        dialog(_("エラー"), _("操作が定義されていないメニューです。"))
        return

    def OnMenuOpen(self, event):
        # メニューの有効・無効を切り替える
        disableMenuIdSet = views.menuBlocker.testMenu(self.parent.activeTab)
        for i in event.GetEventObject().GetMenuItems():
            i.Enable(not i.GetId() in disableMenuIdSet)

        # カラムソートメニューの場合、中身の描画をする
        if event.GetMenu() == self.parent.menu.hMenuBar.FindItemById(
                menuItemsStore.getRef("VIEW_SORT_COLUMN")).GetSubMenu():
            menu = self.parent.menu.hMenuBar.FindItemById(
                menuItemsStore.getRef("VIEW_SORT_COLUMN")).GetSubMenu()
            # 一旦全て削除
            for i in range(menu.GetMenuItemCount()):
                menu.DestroyItem(menu.FindItemByPosition(0))

            # カラム数分登録
            i = 0
            for title in self.parent.activeTab.GetListColumns():
                subMenu = wx.Menu()
                subMenu.Append(constants.MENU_ID_SORT_COLUMN + 2 * i, "前へ")
                subMenu.Append(
                    constants.MENU_ID_SORT_COLUMN + 2 * i + 1, "後ろへ")
                menu.AppendSubMenu(subMenu, title)
                i += 1
            menu.Enable(constants.MENU_ID_SORT_COLUMN, False)
            menu.Enable(constants.MENU_ID_SORT_COLUMN + 2 * (i - 1) + 1, False)
        event.Skip()

    def ColumnSort(self, menuId):
        order = self.parent.activeTab.GetColumnOrderList()
        if menuId % 2 == 0:  # 前へ
            target = int((menuId - constants.MENU_ID_SORT_COLUMN) / 2)
            tmp = order[target]
            order[target] = order[target - 1]
            order[target - 1] = tmp
        else:  # 後ろへ
            target = int((menuId - constants.MENU_ID_SORT_COLUMN - 1) / 2)
            tmp = order[target]
            order[target] = order[target + 1]
            order[target + 1] = tmp
        self.parent.activeTab.SetColumnOrderList(order)

    def StartRename(self):
        """リネームを開始する。"""
        self.parent.activeTab.StartRename()
    # end StartRename

    def DelaiedCall(self, callable):
        """メニューから、すぐに何かを読み上げる機能を実行すると、メニューが閉じてリストに戻った読み上げにかき消されてしまう。なので、エンターが押されているかどうかを判定して、その場合にcallableの実行時間を遅らせる。"""
        if not wx.GetKeyState(wx.WXK_RETURN):
            callable()
            return
        else:
            later = wx.CallLater(200, callable)
    # end delaiedCall

    def ShowVersionInfo(self):
        """バージョン情報を表示する。"""
        dialog(
            _("バージョン情報"),
            _("%(app)s Version %(ver)s.\nCopyright (C) %(year)s %(names)s") % {
                "app": constants.APP_NAME,
                "ver": constants.APP_VERSION,
                "year": constants.APP_COPYRIGHT_YEAR,
                "names": constants.APP_DEVELOPERS})

    def ExecProgram(self):
        d = views.SympleImputDialog.Dialog(_("ファイル名を指定して実行"), _("コマンドライン"))
        d.Initialize()
        if d.Show() == wx.ID_CANCEL:
            return
        val = d.GetValue()
        self.parent.activeTab.ExecProgram(val)

    def GoBackward(self):
        """back アクションを実行"""
        ret = self.parent.activeTab.GoBackward()
        if ret == errorCodes.BOUNDARY:
            globalVars.app.PlaySound(
                globalVars.app.config["sounds"]["boundary"])

    def OpenNewTab(self):
        """選択中のディレクトリを新しいタブで開く"""
        e = self.parent.activeTab.GetFocusedElement()
        self.parent.Navigate(e.fullpath, as_new_tab=True)

    def CloseTab(self):
        self.parent.CloseTab(self.parent.activeTab)

    def NewTab(self):
        if os.path.isdir(
            os.path.expandvars(
                globalVars.app.config["browse"]["startPath"])):
            self.parent.Navigate(
                os.path.expandvars(
                    globalVars.app.config["browse"]["startPath"]),
                as_new_tab=True)
        else:
            self.parent.Navigate("", as_new_tab=True)

    def Search(self):
        basePath = self.parent.activeTab.listObject.rootDirectory
        out_lst = []  # 入力画面が出てるときに、もうファイルリスト取得を開始してしまう
        task = workerThreads.RegisterTask(
            workerThreadTasks.GetRecursiveFileList, {
                'path': basePath, 'out_lst': out_lst, 'eol': True})

        searchHistory = history.History(
            globalVars.app.config.getint(
                "search", "history_count", 0, 0, 100), False)
        grepHistory = history.History(
            globalVars.app.config.getint(
                "search", "history_count", 0, 0, 100), False)
        hist = {}
        try:
            with open(constants.HISTORY_FILE_NAME, 'rb') as f:
                hist = pickle.load(f)
                searchHistory.lst = hist["search"]
                searchHistory.cursor = len(hist["search"]) - 1
                grepHistory.lst = hist["grep"]
                grepHistory.cursor = len(hist["grep"]) - 1
        except BaseException:
            pass

        d = views.search.Dialog(
            basePath, list(
                reversed(
                    searchHistory.getList())), list(
                reversed(
                    grepHistory.getList())))
        d.Initialize()
        canceled = False
        while(True):
            ret = d.Show()
            if ret == wx.ID_CANCEL:
                task.Cancel()
                canceled = True
                break
            # end キャンセルして抜ける
            val = d.GetValue()
            if val['isRegularExpression']:
                ret = misc.ValidateRegularExpression(val['keyword'])
                if ret != "OK":
                    dialog(
                        _("エラー"),
                        _("正規表現の文法が間違っています。\nエラー内容: %(error)s") % {
                            'error': ret})
                    continue
                # end 正規表現違う
            # end 正規表現モードがオンかどうか
            break
        # end 入力が正しくなるまで
        if canceled:
            return
        actionstr = "search" if val['type'] == 0 else "grep"
        target = {
            'action': actionstr,
            'basePath': basePath,
            'out_lst': out_lst,
            'keyword': val['keyword'],
            'isRegularExpression': val['isRegularExpression']}
        self.parent.Navigate(target, as_new_tab=True)

        if val['type'] == 0:
            searchHistory.add(val['keyword'])
        else:
            grepHistory.add(val['keyword'])
        hist["search"] = searchHistory.getList()
        hist["grep"] = grepHistory.getList()
        try:
            with open(constants.HISTORY_FILE_NAME, 'wb') as f:
                pickle.dump(hist, f)
        except BaseException:
            pass

    def GoForward(self, stream=False, admin=False):
        """forward アクションを実行。stream=True で、ファイルを開く代わりにストリームを開く。admin=True で、管理者モード。"""
        ret = self.parent.activeTab.GoForward(stream, admin)

    def SortNext(self):
        """sortNext アクションを実行。"""
        p = self.parent
        ret = p.activeTab.SortNext()
        if ret == errorCodes.NOT_SUPPORTED:
            dialog(_("エラー"), _("このオペレーションはサポートされていません。"))

    def SortSelect(self):
        """並び順を指定する。"""
        t = self.parent.activeTab
        t.SortSelect()

    def SortCycleAd(self):
        t = self.parent.activeTab
        t.SortCycleAd()

    def UpdateFilelist(self, silence=False):
        ret = self.parent.activeTab.UpdateFilelist(silence=silence)

    def OpenContextMenu(self, silence=True):
        self.parent.activeTab.OpenContextMenu(event=None)

    def ShowDetail(self, elem):
        d = views.objectDetail.Dialog()
        d.Initialize()
        d.add(_("名前"), elem.basename)
        d.add(_("パス"), elem.fullpath)
        if isinstance(
                elem,
                browsableObjects.File) or isinstance(
                elem,
                browsableObjects.Stream):
            if elem.size >= 0:
                d.add(
                    _("サイズ"),
                    misc.ConvertBytesTo(
                        elem.size,
                        misc.UNIT_AUTO,
                        True))
                d.add(_("サイズ(バイト)"), elem.size)
                if isinstance(elem, browsableObjects.Folder):
                    d.add(
                        _("内容"), _("ファイル数： %d サブディレクトリ数： %d") %
                        (elem.fileCount, elem.dirCount))
            elif isinstance(elem, browsableObjects.Folder):
                d.add(_("サイズ"), d.CALCURATING)
                d.add(_("サイズ(バイト)"), d.CALCURATING)
                d.add(_("内容"), d.CALCURATING)
                param = {'lst': [(0, elem.fullpath)],
                         'callback': d.setDirCalcResult}
                d.setTask(
                    workerThreads.RegisterTask(
                        workerThreadTasks.DirCalc, param))
        if isinstance(elem, browsableObjects.File):
            d.add(_("作成日時"), elem.creationDate.strftime("%Y/%m/%d(%a) %H:%M:%S"))
            d.add(_("更新日時"), elem.modDate.strftime("%Y/%m/%d(%a) %H:%M:%S"))
            d.add(_("属性"), elem.longAttributesString)
            d.add(_("種類"), elem.typeString)
            if not elem.shortName == "":
                d.add(_("短い名前"), elem.shortName)
            else:
                d.add(_("短い名前"), _("なし"))

            h = win32file.CreateFile(
                elem.fullpath,
                0,
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                None,
                win32file.OPEN_EXISTING,
                win32file.FILE_FLAG_BACKUP_SEMANTICS,  # これがないとディレクトリを開けない
                0)
            info = win32file.GetFileInformationByHandleEx(
                h, win32file.FileStandardInfo)
            if info:
                d.add(_("消費ディスク領域"),
                      misc.ConvertBytesTo(info["AllocationSize"],
                                          misc.UNIT_AUTO,
                                          True) + " (" + str(info["AllocationSize"]) + " bytes)")
                tmp = ""
                if info["DeletePending"]:
                    tmp += _("削除予約済 ")
                if info["NumberOfLinks"] > 1:
                    tmp += _("ハードリンクにより他の%d 箇所から参照 " %
                             (info["NumberOfLinks"] - 1))
                if tmp == "":
                    tmp = _("なし")
                d.add(_("追加情報"), tmp)

        if isinstance(elem, browsableObjects.Drive):
            if elem.free >= 0:
                d.add(
                    _("フォーマット"),
                    fileSystemManager.GetFileSystemObject(
                        elem.letter))
                if elem.total > 0:
                    d.add(
                        _("空き容量"),
                        "%s (%s%%)" %
                        (misc.ConvertBytesTo(
                            elem.free,
                            misc.UNIT_AUTO,
                            True),
                            elem.free *
                            100 //
                            elem.total))
                else:
                    d.add(
                        _("空き容量"),
                        misc.ConvertBytesTo(
                            elem.free,
                            misc.UNIT_AUTO,
                            True))
                d.add(
                    _("総容量"),
                    misc.ConvertBytesTo(
                        elem.total,
                        misc.UNIT_AUTO,
                        True))
            else:
                d.add(_("フォーマット"), _("未挿入"))
            d.add(_("種類"), elem.typeString)
        if isinstance(
                elem,
                browsableObjects.NetworkResource) and elem.address != "":
            d.add(_("IPアドレス"), elem.address)
        d.Show()
        return
