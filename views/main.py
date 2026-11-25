# -*- coding: utf-8 -*-
# Falcon app main view
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2021 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
falconのメインウィンドウ。

viewkit.MainWindow を土台に、falcon固有の以下の機能を追加している。
- タブ(ファイル一覧・ドライブ一覧など)の管理
- タブの種類や選択項目に応じたメニューの無効化(views.menuBlocker)
- タブの種類によって同じキーを別の機能に割り当てるショートカットキー(keymap)
- お気に入りフォルダ・「ここで開く」など、設定に応じて追加されるメニュー
- カラムの並び替えメニュー
- 名前の変更中などにショートカットキーとメニューを無効化する機能
"""

import ctypes
import os
import pickle
import sys

import history
import pywintypes
import viewkit
import viewkit.presets.keyValueSetting
import win32file
import wx

from logging import getLogger
from viewkit.menu import Menu as ViewkitMenu

import archiver
import background_wait
import browsableObjects
import constants
import content_reader
import defaultKeymap
import deviceCtrl
import errorCodes
import fileSystemManager
import globalVars
import keymap
import menuItemsDic
import menuItemsStore
import misc
import network_resource
import operation_manager
import reparse_link
import shortcut_link
import tabs.navigator
import views.bulk_rename
import views.changeAttribute
import views.compress
import views.extract
import views.favoriteDirectory
import views.fonttest
import views.globalKeyConfig
import views.key_value_setting
import views.makeHash
import views.makeShortcut
import views.menuBlocker
import views.new_file
import views.new_shortcut
import views.objectDetail
import views.openHere
import views.operation_progress
import views.registerOriginalAssociation
import views.search
import views.settingsDialog
import views.SimpleInputDialog
import views.versionDialog
import views.ViewCreator
import workerThreads
import workerThreadTasks

from simpleDialog import dialog

# 適当な数字。そのイベントは自分自身で投げたものであることを示している
EVENT_FROM_SELF = -1

# キーマップ上でのメインウィンドウの識別子
KEYMAP_IDENTIFIER = "mainView"


class UserMenuItemDefinition(viewkit.MenuItemDefinition):
    """ユーザが名前を付けたメニュー項目。アクセスキーを持たず、名前をそのまま表示する。"""

    def __init__(self, identifier: str, display_name: str):
        self.identifier = identifier
        self.display_name = display_name
        self.accessor_letter = None
        self.sub_menu_items = None

    def getDisplayString(self) -> str:
        return self.display_name


def _menu_item(identifier: str, accessor_letter: str) -> viewkit.MenuItemDefinition:
    """menuItemsDic の表示名を使ってメニュー項目の定義を作る"""
    # 表示名に含まれるアクセスキー表記は、viewkitが付けるので取り除く
    name = menuItemsDic.dic[identifier].replace("(&%s)" % accessor_letter, "")
    return viewkit.MenuItemDefinition(identifier, name, accessor_letter)


class MainWindow(viewkit.MainWindow):
    def __init__(self, ctx: viewkit.ApplicationContext):
        self.app = globalVars.app
        self.log = getLogger("%s.mainView" % constants.LOG_PREFIX)
        self.log.debug("created")
        self.timer = misc.Timer()
        self.shortcut_enabled = True
        self.tabs = []
        self.active_tab = None
        super().__init__(ctx)

        # メニューのrefは、falcon全体で使っている menuItemsStore で管理する
        self.window_ctx.ref_store = menuItemsStore.getStore()

        title = ""
        if ctypes.windll.shell32.IsUserAnAdmin():
            title += "[" + _("管理者") + "]"
        title += constants.APP_NAME
        self.SetTitle(title)

        self.menu = FalconMenu(self, KEYMAP_IDENTIFIER)
        self._add_user_command_keys()

        self.tab_ctrl = self.creator.tabCtrl(_("タブ選択"), self._on_change_tab, 0, wx.EXPAND, 1)
        # 実行中のファイル操作の進み具合。操作がない間は隠す
        self.progress_gauge, dummy = self.creator.gauge(_("ファイル操作の進行状況"), text_layout=None)
        self.progress_gauge.SetRange(100)
        self.progress_gauge.Hide()
        self._progress_window_opened = False
        self.operations = operation_manager.OperationManager(self)
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_MENU_OPEN, self._on_menu_open)

    # ---- viewkit.MainWindow のオーバーライド ----

    def define_features(self):
        features = []
        handlers = self._get_feature_handlers()
        for identifier, display_name in menuItemsDic.dic.items():
            if identifier == "":
                continue
            features.append(viewkit.Feature(identifier, display_name, None, handlers.get(identifier)))
        # お気に入りフォルダと「ここで開く」
        for manager in self.app.user_command_managers:
            for name in manager.paramMap:
                identifier = (manager.refHead + name).upper()
                features.append(viewkit.Feature(identifier, name, None, self._on_user_command))
        return features

    def define_menu(self):
        return viewkit.MenuDefinition(
            viewkit.TopMenuDefinition(_("ファイル"), "F", [
                _menu_item("FILE_RENAME", "R"),
                _menu_item("FILE_BULK_RENAME", "B"),
                _menu_item("FILE_CHANGEATTRIBUTE", "A"),
                _menu_item("FILE_MAKESHORTCUT", "S"),
                _menu_item("FILE_TRASH", "T"),
                _menu_item("FILE_DELETE", "D"),
                _menu_item("FILE_VIEW_DETAIL", "I"),
                _menu_item("FILE_SHOWPROPERTIES", "P"),
                viewkit.MenuItemDefinition("FILE_NEW", menuItemsDic.dic["FILE_NEW"], "N", [
                    _menu_item("FILE_MKDIR", "D"),
                    _menu_item("FILE_MKFILE", "F"),
                    _menu_item("FILE_MKSHORTCUT", "S"),
                ]),
                _menu_item("FILE_FILEOPTEST", "O"),
                _menu_item("FILE_EXIT", "X"),
            ]),
            viewkit.TopMenuDefinition(_("編集"), "E", [
                _menu_item("EDIT_COPY", "C"),
                _menu_item("EDIT_CUT", "X"),
                _menu_item("EDIT_PAST", "V"),
                _menu_item("EDIT_PAST_SHORTCUT", "T"),
                _menu_item("EDIT_NAMECOPY", "N"),
                _menu_item("EDIT_FULLPATHCOPY", "F"),
                _menu_item("EDIT_SELECTALL", "A"),
                _menu_item("EDIT_SEARCH", "S"),
                _menu_item("EDIT_UPDATEFILELIST", "U"),
                _menu_item("EDIT_MARKITEM", "K"),
                _menu_item("EDIT_MARKITEM_ALL", "L"),
                _menu_item("EDIT_UNMARKITEM_ALL", "E"),
                _menu_item("EDIT_MARKITEM_INVERSE", "I"),
                _menu_item("EDIT_OPENCONTEXTMENU", "M"),
            ]),
            viewkit.TopMenuDefinition(_("移動"), "M", [
                _menu_item("MOVE_FORWARD", "O"),
                _menu_item("MOVE_FORWARD_ADMIN", "A"),
                _menu_item("MOVE_EXEC_ORIGINAL_ASSOCIATION", "E"),
                _menu_item("MOVE_FORWARD_TAB", "T"),
                _menu_item("MOVE_FORWARD_STREAM", "S"),
                _menu_item("MOVE_BACKWARD", "U"),
                _menu_item("MOVE_NEWTAB", "N"),
                _menu_item("MOVE_CLOSECURRENTTAB", "C"),
                _menu_item("MOVE_TOPFILE", "F"),
                _menu_item("MOVE_SPECIAL_UP", "P"),
                _menu_item("MOVE_SPECIAL_DOWN", "D"),
                _menu_item("MOVE_HIST_NEXT", "X"),
                _menu_item("MOVE_HIST_PREV", "V"),
                _menu_item("MOVE_MARKSET", "K"),
                _menu_item("MOVE_MARK", "M"),
                _menu_item("MOVE_INPUT_DIR", "I"),
                self._user_command_menu(self.app.favorite_directory, "G", ("MOVE_ADD_FAVORITE", "MOVE_SETTING_FAVORITE")),
                self._user_command_menu(self.app.open_here_command, "H", ("MOVE_SETTING_OPEN_HERE",)),
            ]),
            viewkit.TopMenuDefinition(_("読み"), "R", [
                viewkit.MenuItemDefinition("READ_PREVIEW", menuItemsDic.dic["READ_PREVIEW"], "P", [
                    _menu_item("READ_CONTENT_PREVIEW", "P"),
                    _menu_item("READ_CONTENT_READHEADER", "H"),
                    _menu_item("READ_CONTENT_READFOOTER", "F"),
                ]),
                _menu_item("READ_CURRENTFOLDER", "C"),
                _menu_item("READ_LISTITEMNUMBER", "N"),
                _menu_item("READ_LISTINFO", "I"),
                _menu_item("READ_PROGRESS", "G"),
                _menu_item("READ_SETMOVEMENTREAD", "M"),
            ]),
            viewkit.TopMenuDefinition(_("ツール"), "T", [
                _menu_item("TOOL_COMPRESS", "C"),
                _menu_item("TOOL_EXTRACT", "X"),
                _menu_item("TOOL_DIRCALC", "D"),
                _menu_item("TOOL_HASHCALC", "H"),
                _menu_item("TOOL_EXEC_PROGRAM", "R"),
                _menu_item("TOOL_ADDPATH", "P"),
                _menu_item("TOOL_EJECT_DRIVE", "E"),
                _menu_item("TOOL_EJECT_DEVICE", "V"),
            ]),
            viewkit.TopMenuDefinition(_("表示"), "V", [
                _menu_item("VIEW_SORTNEXT", "N"),
                _menu_item("VIEW_SORTSELECT", "S"),
                _menu_item("VIEW_SORTCYCLEAD", "A"),
                _menu_item("VIEW_DRIVE_INFO", "D"),
                _menu_item("VIEW_TOGGLE_EXTENSION", "E"),
                _menu_item("VIEW_PROGRESS", "P"),
            ]),
            viewkit.TopMenuDefinition(_("環境"), "O", [
                _menu_item("ENV_REGIST_ORIGINAL_ASSOCIATION", "A"),
                _menu_item("ENV_KEY_CONFIG", "K"),
                _menu_item("ENV_TESTDIALOG", "T"),
                _menu_item("ENV_FONTTEST", "F"),
                _menu_item("ENV_SETTINGS", "S"),
            ]),
            viewkit.TopMenuDefinition(_("ヘルプ"), "H", [
                _menu_item("HELP_VERINFO", "V"),
                _menu_item("HELP_UPDATE", "U"),
            ]),
        )

    def _user_command_menu(self, manager, accessor_letter, fixed_items):
        """お気に入りフォルダ・「ここで開く」のサブメニュー定義を作る"""
        items = [UserMenuItemDefinition((manager.refHead + name).upper(), name) for name in manager.paramMap]
        items += [_menu_item(identifier, letter) for identifier, letter in zip(fixed_items, ("A", "S"))]
        return viewkit.MenuItemDefinition(manager.refHead, self.app.user_command_managers[manager], accessor_letter, items)

    def onOpen(self):
        self._make_first_tab()
        if self.active_tab is not None:
            self.active_tab.hListCtrl.SetFocus()
        self.log.debug("Finished creating main view (%f seconds)" % self.timer.elapsed)

    def _applyCustomShortcuts(self):
        # ショートカットキーは、タブの種類による重複を許すfalcon独自のキーマップ(self.menu.keymap)で管理する
        pass

    def _setupMenuBar(self):
        super()._setupMenuBar()
        bar = self.GetMenuBar()
        # カラムの並び替えメニューは、メニューを開いたときに中身を作る
        view_menu = bar.GetMenu(bar.FindMenu(_("表示")))
        view_menu.Append(wx.MenuItem(view_menu, menuItemsStore.getRef("VIEW_SORT_COLUMN"), menuItemsDic.dic["VIEW_SORT_COLUMN"] + "(&C)", subMenu=wx.Menu()))
        self.menu.set_menu_bar(bar)

    def _generateMenuItem(self, menu, ref, item):
        menu_item = super()._generateMenuItem(menu, ref, item)
        # falcon独自のキーマップで設定されたショートカットキーを表示する
        shortcut = self.menu.get_key_string(item.identifier) if item.identifier else None
        if shortcut and menu_item.GetSubMenu() is None:
            menu_item.SetItemLabel("%s\t%s" % (item.display_name, shortcut))
        return menu_item

    def _applyAcceleratorTable(self):
        # ショートカットキーは、アクティブなタブのリストに対して登録する
        if self.active_tab is not None and self.shortcut_enabled:
            self.menu.apply_shortcut(self.active_tab.hListCtrl)

    def _receiveMenuCommand(self, event):
        """メニュー項目が選択されたときのイベントハンドラ。"""
        # ショートカットキーが無効状態のときは何もしない
        if not self.shortcut_enabled or self.active_tab is None:
            event.Skip()
            return

        # プレビュー再生停止等のため、キー押下をタブへ通知
        # ここにきている場合KeyDownイベントはとれないため
        self.active_tab.OnKeyDown()

        selected = event.GetId()

        # カラムソートは特別対応
        if selected >= constants.MENU_ID_SORT_COLUMN:
            self._column_sort(selected)
            return

        # キー重複対応のためのIDの場合には、イベントを投げ直す
        # 複数投げられるが、有効状態のものは１つだけなはず
        if self.menu.keymap.is_shared_ref(selected):
            for ref in self.menu.keymap.get_original_refs(selected):
                new_event = wx.CommandEvent(event.GetEventType(), ref)
                new_event.SetExtraLong(EVENT_FROM_SELF)  # キー操作無効を示す音を鳴らさない
                wx.PostEvent(self.GetEventHandler(), new_event)
            return

        # 選択された(ショートカットで押された)メニューが無効状態なら何もしない
        if selected in views.menuBlocker.testMenu(self.active_tab):
            if not event.GetExtraLong() == EVENT_FROM_SELF:
                self.app.play_sound(self.app.settings.get("sounds", "boundary"))
            event.Skip()
            return

        identifier = self.window_ctx.ref_store.getIdentifier(selected)
        feature = self.window_ctx.feature_store.getByIdentifier(identifier) if identifier else None
        if feature is None or feature.action is None:
            dialog(_("エラー"), _("操作が定義されていないメニューです。"))
            return
        feature.action(event)

    def _windowMove(self, event):
        # viewkitの設定は負の座標を受け付けないので、最大化時などは保存しない
        position = self.GetPosition()
        if position.x >= 0 and position.y >= 0:
            super()._windowMove(event)
        else:
            event.Skip()

    # ---- タブ管理 ----

    def _make_first_tab(self):
        """最初のタブを作成する。"""
        if len(sys.argv) > 1:
            result = self.navigate(misc.analyzeUserInputPath(sys.argv[1], os.getcwd()), as_new_tab=True)
            if result == errorCodes.OK:
                return
            if result not in (errorCodes.CANCELED, errorCodes.NETWORK_UNAVAILABLE):  # 理由を既に知らせている
                dialog("Error", _("引数で指定されたディレクトリ '%(dir)s' は存在しません。") % {"dir": sys.argv[1]})
        start_path = self.app.settings.get("browse", "startpath")
        if start_path != "":
            result = self.navigate(misc.analyzeUserInputPath(start_path, os.getcwd()), as_new_tab=True)
        else:  # ドライブ一覧を表示
            result = self.navigate("", as_new_tab=True)
        if result == errorCodes.OK:
            return
        # 中止した場合や接続できない場合は、既に知らせている
        already_notified = result in (errorCodes.CANCELED, errorCodes.NETWORK_UNAVAILABLE)
        if not already_notified and os.path.abspath(os.path.expandvars(start_path)) != "":
            dialog("Error", _("設定された起動時ディレクトリ '%(dir)s' は存在しません。") % {"dir": start_path})
        result = self.navigate("", as_new_tab=True)
        if result != errorCodes.OK:
            dialog("Error", _("ドライブ一覧の読み込みに失敗しました。大変お手数ですが、ログファイルを添付して開発者までお問い合わせください。"))

    def navigate(self, target, as_new_tab=False):
        """指定のパスにナビゲートする。"""
        if isinstance(target, dict):
            self.log.debug("Creating new tab %s..." % target['action'])
        else:
            self.log.debug("Creating new tab %s..." % target)
        wx.CallLater(200, self._say_new_tab)
        panel = views.ViewCreator.makePanel(self.tab_ctrl)
        creator = views.ViewCreator.ViewCreator(1, panel, None)
        new_tab = tabs.navigator.Navigate(target, create_new_tab_info=(self, creator))
        if isinstance(new_tab, int):  # Error
            return new_tab
        self.tabs.append(new_tab)
        self.tab_ctrl.InsertPage(len(self.tabs) - 1, panel, new_tab.GetTabName(), False)
        self.activate_tab(len(self.tabs) - 1)
        return errorCodes.OK

    def _say_new_tab(self):
        s = _("新しいタブ") if len(self.tabs) > 1 else _("falcon")
        self.app.say(s, interrupt=True)

    def replace_current_tab(self, new_tab):
        """現在のタブのインスタンスを入れ替える。ファイルリストからドライブリストになったときなどに使う。"""
        i = self.get_tab_index(self.active_tab)
        if i == -1:
            return  # 最初のタブの作成

        self._update_menu_state(new_tab)
        self.tabs[i] = new_tab
        self.active_tab.OnBeforeChangeTab()
        self.active_tab.OnClose()
        self.active_tab = new_tab
        self._applyAcceleratorTable()

        # タブ名変更。active_tab書き換え後に呼ぶ必要がある
        self.update_tab_name()

    def activate_tab(self, page_no, trigger_on_reactivate=False):
        """指定されたインデックスのタブをアクティブにする。"""
        self._update_menu_state(self.tabs[page_no])
        self.active_tab = self.tabs[page_no]
        self.tab_ctrl.SetSelection(page_no)
        self._applyAcceleratorTable()
        if trigger_on_reactivate:
            self.active_tab.onReactivate()

    def close_tab(self, page_no):
        """指定されたインデックスのタブを閉じる。閉じたタブがアクティブだった場合は、別のタブをアクティブ状態にする。全てのタブが閉じられた場合は、終了イベントを投げる。"""
        if not isinstance(page_no, int):  # 数字じゃなくてタブオブジェクトが渡ってた
            page_no = self.get_tab_index(page_no)
            if page_no == -1:
                return

        if len(self.tabs) == 1:  # 最後のタブなのでソフト終了
            tab = self.tabs[0]
            if self.Close():  # 終了の確認で取りやめた場合は、タブを残す
                tab.OnClose()
            return
        active_tab = self.active_tab
        popped_tab = self.tabs.pop(page_no)
        popped_tab.OnClose()
        # この時点で、 noteBook がリストコントロールをデリートするらしいので、他の場所で明示的に消してはいけないとリファレンスに書いてある
        self.tab_ctrl.DeletePage(page_no)
        self.tab_ctrl.SendSizeEvent()
        if active_tab is popped_tab:  # アクティブなタブを閉じた場合に後ろのタブを持って来る
            new_page_no = min(page_no, len(self.tabs) - 1)
            self.activate_tab(new_page_no, trigger_on_reactivate=True)

    def get_number_of_tabs(self):
        return len(self.tabs)

    def get_tab_index(self, target):
        """targetで指定されたタブがtabsの中でインデックス何番か取得"""
        for i, elem in enumerate(self.tabs):
            if elem is target:
                return i
        return -1

    def _on_change_tab(self, event):
        """タブ変更イベント"""
        self.active_tab.OnBeforeChangeTab()
        self.activate_tab(event.GetSelection())

    def update_file_lists(self, directories):
        """指定されたディレクトリを表示しているファイル一覧のタブを、最新の状態に更新する。"""
        directories = {os.path.normcase(directory) for directory in directories}
        for tab in self.tabs:
            # 検索結果のタブは FileListTab の派生だが、再検索になるため更新しない
            if type(tab) is tabs.fileList.FileListTab and os.path.normcase(tab.listObject.rootDirectory) in directories:
                tab.UpdateFilelist(silence=True)

    def can_update_in_background(self):
        """利用者の操作を妨げずに、一覧を更新できるかどうかを返す。名前の変更中や、ダイアログを開いている間は更新しない。"""
        return self.shortcut_enabled and self.IsEnabled()

    def can_ask(self):
        """確認のダイアログを出してよいかどうかを返す。ほかのアプリの操作中や、名前の変更中などは出さない。"""
        return self.can_update_in_background() and self.IsActive()

    def refresh_file_lists(self, directories, deleted_paths=()):
        """
        update_file_lists と同じだが、カーソルの位置、選択、チェックを維持する。ファイル操作が終わったときに使う。
        検索結果の一覧からは、deleted_paths とその中の項目のうち、なくなったものを取り除く。
        """
        directories = {os.path.normcase(directory) for directory in directories}
        for tab in self.tabs:
            # 検索結果のタブは FileListTab の派生だが、再検索になるため更新しない
            if type(tab) is tabs.fileList.FileListTab and os.path.normcase(tab.listObject.rootDirectory) in directories:
                self._refresh_file_list(tab)
            elif deleted_paths and isinstance(tab, (tabs.searchResult.SearchResultTab, tabs.grepResult.GrepResultTab)):
                self._remove_deleted_results(tab, deleted_paths)
        self._update_menu_state(self.active_tab)

    def _remove_deleted_results(self, tab, deleted_paths):
        # 検索中は結果が追加され続けているため、変更しない
        if not tab.tempListObject.GetFinishedStatus():
            return
        prefixes = tuple(os.path.join(os.path.normcase(path), "") for path in deleted_paths)

        def is_deleted(element):
            return os.path.join(os.path.normcase(element.fullpath), "").startswith(prefixes) and not os.path.lexists(element.fullpath)

        old_items = list(tab.listObject.GetItemList())
        if not any(is_deleted(element) for element in old_items):
            return
        focused = tab.GetFocusedElement()
        index = tab.GetFocusedItem()
        for elements in tab.listObject.lists:
            elements[:] = [element for element in elements if not is_deleted(element)]
        items = list(tab.listObject.GetItemList())
        if focused in items:
            cursor = items.index(focused)
        else:
            cursor = min(index, len(items) - 1)
        # 検索結果のアイコンのハンドルは破棄されているので、一覧を作り直さず、登録済みの画像のまま行だけを入れ替える
        tab.checkedItem &= set(items)
        tab.hListCtrl.set_items(items)
        tab.Focus(cursor)

    def _refresh_file_list(self, tab):
        index = tab.GetFocusedItem()
        old_paths = tab.listObject.GetItemPaths()
        selected = set()
        i = tab.hListCtrl.GetFirstSelected()
        while i >= 0:
            selected.add(tab.listObject.GetElement(i).fullpath)
            i = tab.hListCtrl.GetNextSelected(i)
        focused = tab.GetFocusedElement()
        checked = {element.fullpath for element in tab.checkedItem}
        if tab.UpdateFilelist(silence=True) is not None:
            return  # 更新できなかった
        items = list(tab.listObject.GetItemList())
        if not items:
            return
        if focused is not None and focused.fullpath not in {item.fullpath for item in items}:
            # カーソルのあった項目がなくなった
            tab.Focus(min(tab._findFocusAfterDeletion(old_paths, index), len(items) - 1))
        for i, item in enumerate(items):
            if item.fullpath in selected:
                tab.hListCtrl.Select(i)
            if item.fullpath in checked:
                tab.checkedItem.add(item)
                tab.hListCtrl.SetItemBackgroundColour(i, "#0000FF")
                tab.hListCtrl.RefreshItem(i)

    def set_progress(self, percentage):
        """プログレスバーに割合を表示する。None なら隠す。"""
        visible = percentage is not None and not self._progress_window_opened
        if visible and self.progress_gauge.GetValue() != percentage:
            self.progress_gauge.SetValue(percentage)
        # 名前の変更中に一覧の大きさが変わると、編集が打ち切られてしまう
        if visible != self.progress_gauge.IsShown() and self.shortcut_enabled:
            self.progress_gauge.Show(visible)
            self.creator.getPanel().Layout()

    def _on_view_progress(self, event):
        """ファイル操作の進行状況を表示する"""
        # スクリーンリーダーの報告が重ならないよう、プログレスバーはどちらか一方だけに表示する
        self._progress_window_opened = True
        self.operations.update_gauge()
        try:
            self.showSubWindow(views.operation_progress.OperationProgressWindow, _("ファイル操作の進行状況"), self.operations)
        finally:
            self._progress_window_opened = False
            self.operations.update_gauge()

    def update_tab_name(self):
        """タブ名変更の可能性があるときにtabsからたたかれる"""
        index = self.get_tab_index(self.active_tab)
        if index >= 0:
            self.tab_ctrl.SetPageText(index, self.active_tab.GetTabName())

    def _update_menu_state(self, new):
        # メニューの有効・無効を変更
        self.menu.enable("MOVE_MARK", new.IsMarked())
        self.menu.enable("EDIT_UNMARKITEM_ALL", new.hasCheckedItem())
        self.menu.enable("EDIT_MARKITEM_ALL", len(new.checkedItem) != len(new.listObject))
        self.menu.enable("MOVE_HIST_NEXT", new.environment["history"].hasNext())
        self.menu.enable("MOVE_HIST_PREV", new.environment["history"].hasPrevious())

    def _on_close(self, event):
        """ウィンドウが閉じられる直前に呼ばれる。"""
        self.log.info("received close event(force=" + ("true" if not event.CanVeto() else "false") + ")")
        if not event.CanVeto():  # 強制シャットダウン
            self.operations.shutdown()
            self.Destroy()
            return
        if not self._confirm_stop_operations():
            event.Veto()
            return
        num = self.get_number_of_tabs()
        if num > 1:
            dlg = wx.MessageDialog(
                self,
                _("%(tabs)d個のタブが開いています。これらのタブを全て閉じて、Falconを終了してもよろしいですか？") % {'tabs': num},
                _("終了確認"),
                wx.YES_NO | wx.ICON_QUESTION)
            ret = dlg.ShowModal()
            dlg.Destroy()
            if ret == wx.ID_NO:
                event.Veto()
                self.log.info("CloseEvent.Veto(). user select cancel.")
                return
        self.operations.shutdown()
        event.Skip()

    def _confirm_stop_operations(self):
        """終わっていないファイル操作があれば、終了してよいか確認する。"""
        count = self.operations.get_unfinished_count()
        if count == 0:
            return True
        dlg = wx.MessageDialog(
            self,
            _("%(count)d件のファイル操作が終わっていません。中止して、Falconを終了してもよろしいですか？") % {"count": count},
            _("終了確認"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()
        return result == wx.ID_YES

    # ---- ショートカットキー・メニュー ----

    def set_shortcut_enabled(self, enabled):
        """
                ショートカットキーの有効/無効を切り替える。
                AcceleratorTableとメニューバーのそれぞれに登録されているので、両方の対策が必要。
        """
        self.shortcut_enabled = enabled
        # 名前の変更中にはダミーのメニューバーを出しておく
        # これがないとメニューバーの高さ分リストオブジェクトの大きさが変わってしまうために必要
        self.SetMenuBar(self.menu.menu_bar if enabled else self.menu.disabled_menu_bar)
        # SetMenuBarの後に呼び出しが必要
        self.creator.getSizer().Layout()
        if self.active_tab is not None:
            if enabled:
                self.menu.apply_shortcut(self.active_tab.hListCtrl)
            else:
                self.active_tab.hListCtrl.SetAcceleratorTable(wx.AcceleratorTable())

    def _add_user_command_keys(self):
        """お気に入りフォルダと「ここで開く」のショートカットキーを登録"""
        for target in self.app.user_command_managers:
            for v in target.keyMap:
                if target.keyMap[v] != "":  # キーが指定されていない場合は無視
                    self.menu.keymap.add(target.refHead + v, target.keyMap[v])
        errors = self.menu.keymap.pop_errors()
        if errors:
            message = _("お気に入りディレクトリもしくは「ここで開く」で設定されたショートカットキーが正しくありません。キーが重複しているか、存在しないキー名を指定しています。以下のキーの設定内容をご確認ください。\n\n")
            for v in errors:
                message += v + "\n"
            dialog(_("エラー"), message)

    def update_user_command(self):
        """ショートカットキーやお気に入りフォルダなどの変更を、メニューとキーに反映する"""
        self.menu.init_shortcut()  # キーマップを再取得
        self._add_user_command_keys()  # ユーザコマンドを登録
        # 機能とメニューを作り直す
        self.window_ctx.feature_store = viewkit.FeatureStore()
        self._registerFeatures(self.define_features())
        self._assignRefs()
        self.window_ctx.menu = ViewkitMenu()
        self.window_ctx.menu.setup(self.define_menu())
        self.updateShortcutKeys()
        if not self.shortcut_enabled:
            self.set_shortcut_enabled(False)

    def get_key_entries(self):
        return self.menu.keymap.entries

    def _on_menu_open(self, event):
        # メニューの有効・無効を切り替える
        if self.active_tab is None:
            event.Skip()
            return
        disable_menu_ids = views.menuBlocker.testMenu(self.active_tab)
        obj = event.GetEventObject()
        if obj is None:
            # システムメニューを開いた
            return
        for i in obj.GetMenuItems():
            i.Enable(i.GetId() not in disable_menu_ids)

        # カラムソートメニューの場合、中身の描画をする
        sort_item = self.menu.menu_bar.FindItemById(menuItemsStore.getRef("VIEW_SORT_COLUMN"))
        if sort_item is not None and event.GetMenu() == sort_item.GetSubMenu():
            menu = sort_item.GetSubMenu()
            # 一旦全て削除
            for i in range(menu.GetMenuItemCount()):
                menu.DestroyItem(menu.FindItemByPosition(0))

            # カラム数分登録
            i = 0
            for title in self.active_tab.GetListColumns():
                sub_menu = wx.Menu()
                sub_menu.Append(constants.MENU_ID_SORT_COLUMN + 2 * i, _("前へ"))
                sub_menu.Append(constants.MENU_ID_SORT_COLUMN + 2 * i + 1, _("後ろへ"))
                menu.AppendSubMenu(sub_menu, title)
                i += 1
            menu.Enable(constants.MENU_ID_SORT_COLUMN, False)
            menu.Enable(constants.MENU_ID_SORT_COLUMN + 2 * (i - 1) + 1, False)
        event.Skip()

    def _column_sort(self, menu_id):
        order = self.active_tab.GetColumnOrderList()
        if menu_id % 2 == 0:  # 前へ
            target = (menu_id - constants.MENU_ID_SORT_COLUMN) // 2
            order[target], order[target - 1] = order[target - 1], order[target]
        else:  # 後ろへ
            target = (menu_id - constants.MENU_ID_SORT_COLUMN - 1) // 2
            order[target], order[target + 1] = order[target + 1], order[target]
        self.active_tab.SetColumnOrderList(order)

    # ---- 機能の実装 ----

    def _get_feature_handlers(self):
        """機能の識別子と、その処理を行うメソッドの対応表を返す"""
        tab = self._call_active_tab
        delaied = self._delaied_call_active_tab
        return {
            "FILE_RENAME": tab("StartRename"),
            "FILE_BULK_RENAME": self._on_bulk_rename,
            "FILE_CHANGEATTRIBUTE": self._on_change_attribute,
            "FILE_MAKESHORTCUT": self._on_make_shortcut,
            "FILE_TRASH": tab("Trash"),
            "FILE_DELETE": tab("Delete"),
            "FILE_VIEW_DETAIL": self._on_view_detail,
            "FILE_SHOWPROPERTIES": tab("ShowProperties"),
            "FILE_MKDIR": self._on_make_directory,
            "FILE_MKFILE": self._on_make_file,
            "FILE_MKSHORTCUT": self._on_make_new_shortcut,
            "FILE_FILEOPTEST": tab("FileOperationTest"),
            "FILE_EXIT": self._on_exit,

            "EDIT_COPY": tab("Copy"),
            "EDIT_CUT": tab("Cut"),
            "EDIT_PAST": tab("Past"),
            "EDIT_PAST_SHORTCUT": tab("PasteShortcut"),
            "EDIT_NAMECOPY": tab("NameCopy"),
            "EDIT_FULLPATHCOPY": tab("FullpathCopy"),
            "EDIT_SELECTALL": tab("SelectAll"),
            "EDIT_SEARCH": self._on_search,
            "EDIT_UPDATEFILELIST": self._on_update_file_list,
            "EDIT_MARKITEM": tab("OnSpaceKey"),
            "EDIT_MARKITEM_ALL": tab("CheckAll"),
            "EDIT_UNMARKITEM_ALL": tab("UncheckAll"),
            "EDIT_MARKITEM_INVERSE": tab("CheckInverse"),
            "EDIT_OPENCONTEXTMENU": self._on_open_context_menu,

            "MOVE_FORWARD": self._on_go_forward,
            "MOVE_FORWARD_ADMIN": self._on_go_forward_admin,
            "MOVE_EXEC_ORIGINAL_ASSOCIATION": self._on_exec_original_association,
            "MOVE_FORWARD_TAB": self._on_open_new_tab,
            "MOVE_FORWARD_STREAM": self._on_go_forward_stream,
            "MOVE_BACKWARD": self._on_go_backward,
            "MOVE_NEWTAB": self._on_new_tab,
            "MOVE_CLOSECURRENTTAB": self._on_close_current_tab,
            "MOVE_TOPFILE": tab("GoToTopFile"),
            "MOVE_SPECIAL_UP": lambda event: self.active_tab.Jump(constants.ARROW_UP),
            "MOVE_SPECIAL_DOWN": lambda event: self.active_tab.Jump(constants.ARROW_DOWN),
            "MOVE_HIST_NEXT": tab("GoHistNext"),
            "MOVE_HIST_PREV": tab("GoHistPrevious"),
            "MOVE_MARKSET": self._on_mark_set,
            "MOVE_MARK": tab("GoToMark"),
            "MOVE_INPUT_DIR": self._on_input_dir,
            "MOVE_ADD_FAVORITE": self._on_add_favorite,
            "MOVE_SETTING_FAVORITE": self._on_setting_favorite,
            "MOVE_SETTING_OPEN_HERE": self._on_setting_open_here,

            # tabs/base.py の Preview などは、フォーカスがない・文書を読み取れない場合に例外になるため、content_reader を使う
            "READ_CONTENT_PREVIEW": lambda event: content_reader.preview(self.active_tab),
            "READ_CONTENT_READHEADER": lambda event: self._delaied_call(lambda: content_reader.read_header(self.active_tab)),
            "READ_CONTENT_READFOOTER": lambda event: self._delaied_call(lambda: content_reader.read_footer(self.active_tab)),
            "READ_CURRENTFOLDER": delaied("ReadCurrentFolder"),
            "READ_LISTITEMNUMBER": delaied("ReadListItemNumber"),
            "READ_LISTINFO": delaied("ReadListInfo"),
            "READ_PROGRESS": lambda event: self._delaied_call(self.operations.say_progress),
            "READ_SETMOVEMENTREAD": tab("SetMovementRead"),

            "TOOL_COMPRESS": self._on_compress,
            "TOOL_EXTRACT": self._on_extract,
            "TOOL_DIRCALC": tab("DirCalc"),
            "TOOL_HASHCALC": self._on_hash_calc,
            "TOOL_EXEC_PROGRAM": self._on_exec_program,
            "TOOL_ADDPATH": self._on_add_path,
            "TOOL_EJECT_DRIVE": self._on_eject_drive,
            "TOOL_EJECT_DEVICE": self._on_eject_device,

            "VIEW_SORTNEXT": lambda event: self._delaied_call(self._sort_next),
            "VIEW_SORTSELECT": tab("SortSelect"),
            "VIEW_SORTCYCLEAD": delaied("SortCycleAd"),
            "VIEW_DRIVE_INFO": self._on_drive_info,
            "VIEW_PROGRESS": self._on_view_progress,
            "VIEW_TOGGLE_EXTENSION": lambda event: self._delaied_call(self._toggle_extension),

            "ENV_REGIST_ORIGINAL_ASSOCIATION": self._on_regist_original_association,
            "ENV_KEY_CONFIG": self._on_key_config,
            "ENV_TESTDIALOG": lambda event: None,
            "ENV_FONTTEST": self._on_font_test,
            "ENV_SETTINGS": self._on_settings,

            "HELP_VERINFO": lambda event: self.showSubWindow(views.versionDialog.VersionWindow, _("バージョン情報")),
            "HELP_UPDATE": lambda event: globalVars.update.update(),
        }

    def _call_active_tab(self, method_name):
        """アクティブなタブの指定されたメソッドを呼ぶイベントハンドラを返す"""
        return lambda event: getattr(self.active_tab, method_name)()

    def _delaied_call_active_tab(self, method_name):
        """アクティブなタブの指定されたメソッドを、必要に応じて遅らせて呼ぶイベントハンドラを返す"""
        return lambda event: self._delaied_call(getattr(self.active_tab, method_name))

    def _delaied_call(self, callable):
        """メニューから、すぐに何かを読み上げる機能を実行すると、メニューが閉じてリストに戻った読み上げにかき消されてしまう。なので、エンターが押されているかどうかを判定して、その場合にcallableの実行時間を遅らせる。"""
        if not wx.GetKeyState(wx.WXK_RETURN):
            callable()
        else:
            wx.CallLater(200, callable)

    def _on_user_command(self, event):
        """お気に入りフォルダ・「ここで開く」が選択された"""
        selected = event.GetId()
        for m in self.app.user_command_managers:
            if m.isRefHit(selected):
                if m == self.app.favorite_directory:
                    self.active_tab.Move(misc.analyzeUserInputPath(m.get(selected), self.active_tab.listObject.rootDirectory))
                    # TODO: エラー処理する
                else:  # ここで開く
                    path, prm = misc.PathParamSplit(m.get(selected))
                    prm = prm.replace("%1", self.active_tab.listObject.rootDirectory)
                    misc.RunFile(path, False, prm)
                return

    def _on_exit(self, event):
        self.Close()

    def _on_change_attribute(self, event):
        result = self.showSubWindow(views.changeAttribute.ChangeAttributeWindow, _("属性変更"), self.active_tab.GetSelectedItems().GetAttributeCheckState())
        if result.code == wx.ID_CANCEL:
            return
        self.active_tab.ChangeAttribute(result.user_object)

    def _on_bulk_rename(self, event):
        """選択中の項目の名前を正規表現で一括置換する"""
        # ファイル一覧のタブだけが持つメソッド。ほかのタブでは menuBlocker で無効にしている
        if not hasattr(self.active_tab, "GetBulkRenameTargets"):
            return
        targets = self.active_tab.GetBulkRenameTargets()
        if not targets:
            return
        result = self.showSubWindow(views.bulk_rename.BulkRenameWindow, _("名前の一括置換"), targets)
        if result.code == wx.ID_CANCEL:
            return
        self.active_tab.BulkRename(result.user_object)

    def _on_make_shortcut(self, event):
        target = self.active_tab.GetSelectedItems().GetElement(0)  # browsableObjects
        parameters = views.makeShortcut.MakeShortcutParameters(target.basename, target.canLnkTarget, target.canHardLinkTarget, target.canSynLinkTarget)
        result = self.showSubWindow(views.makeShortcut.MakeShortcutWindow, _("ショートカットの作成"), parameters)
        if result.code == wx.ID_CANCEL:
            return
        self.active_tab.MakeShortcut(result.user_object)

    def _on_view_detail(self, event):
        self.show_detail(self.active_tab.GetFocusedElement())

    def _on_make_directory(self, event):
        value = self.input_text(_("ディレクトリ作成"), _("ディレクトリ名"))
        if value is None:
            return
        self.active_tab.MakeDirectory(value)

    def _on_make_file(self, event):
        # ファイル一覧タブにだけある機能
        if not hasattr(self.active_tab, "MakeFile"):
            return
        directory = self.active_tab.listObject.rootDirectory
        result = self.showSubWindow(views.new_file.NewFileWindow, _("ファイル作成"), directory)
        if result.code == wx.ID_CANCEL:
            return
        self.active_tab.MakeFile(result.user_object)

    def _on_make_new_shortcut(self, event):
        """リンク先を入力して、今のディレクトリに新しいショートカットを作る"""
        # ファイル一覧タブにだけある機能
        if not hasattr(self.active_tab, "MakeNewShortcut"):
            return
        directory = self.active_tab.listObject.rootDirectory
        result = self.showSubWindow(views.new_shortcut.NewShortcutWindow, _("新規ショートカット作成"), directory)
        if result.code == wx.ID_CANCEL:
            return
        self.active_tab.MakeNewShortcut(result.user_object)

    def input_text(self, title, detail, default_value=""):
        """1行の文字列を入力してもらう。キャンセルされたらNoneを返す。"""
        parameters = views.SimpleInputDialog.SimpleInputParameters(detail, default_value)
        result = self.showSubWindow(views.SimpleInputDialog.SimpleInputWindow, title, parameters)
        if result.code == wx.ID_CANCEL:
            return None
        return result.user_object

    def _on_update_file_list(self, event):
        self.update_file_list()

    def update_file_list(self, silence=False):
        self.active_tab.UpdateFilelist(silence=silence)

    def _on_open_context_menu(self, event):
        self.active_tab.OpenContextMenu(event=None)

    def _on_go_forward(self, event):
        self.go_forward()

    def _on_go_forward_admin(self, event):
        self.go_forward(admin=True)

    def _on_go_forward_stream(self, event):
        self.go_forward(stream=True)

    def go_forward(self, stream=False, admin=False):
        """forward アクションを実行。stream=True で、ファイルを開く代わりにストリームを開く。admin=True で、管理者モード。"""
        self.active_tab.GoForward(stream, admin)

    def _on_go_backward(self, event):
        """back アクションを実行"""
        if self.active_tab.GoBackward() == errorCodes.BOUNDARY:
            self.app.play_sound(self.app.settings.get("sounds", "boundary"))

    def _on_exec_original_association(self, event):
        elem = self.active_tab.GetFocusedElement()
        associations = self.app.settings.get_section("originalAssociation")
        if ((not isinstance(elem, browsableObjects.Folder)) and
                isinstance(elem, (browsableObjects.File, browsableObjects.Stream, browsableObjects.GrepItem))):
            extention = os.path.splitext(elem.fullpath)[1][1:].lower()
            if extention in associations:
                command = associations[extention]
            else:
                command = associations.get("<default_file>", "")
        else:
            command = associations.get("<default_dir>", "")
        command = misc.analyzeUserInputPath(command)
        misc.RunFile(command, prm="\"%s\"" % (elem.fullpath))

    def _on_open_new_tab(self, event):
        """選択中のディレクトリを新しいタブで開く"""
        self.navigate(self.active_tab.GetFocusedElement().fullpath, as_new_tab=True)

    def _on_new_tab(self, event):
        start_path = os.path.expandvars(self.app.settings.get("browse", "startpath"))
        if start_path != "" and self._is_available_directory(start_path):
            self.navigate(start_path, as_new_tab=True)
        else:
            self.navigate("", as_new_tab=True)

    def _is_available_directory(self, path):
        """フォルダが存在するかどうかを、ウィンドウを固めずに調べる"""
        try:
            status = network_resource.check_path(path)
        except background_wait.Canceled:
            return False
        return status.exists and not status.is_file

    def _on_close_current_tab(self, event):
        self.close_tab(self.active_tab)

    def _on_mark_set(self, event):
        self.active_tab.MarkSet()
        self.menu.enable("MOVE_MARK", True)

    def _on_input_dir(self, event):
        root_dir = self.active_tab.listObject.rootDirectory
        value = self.input_text(_("パスを指定して移動"), _("移動先"), root_dir)
        if value is None:
            return
        self.active_tab.Move(misc.analyzeUserInputPath(value, self.active_tab.listObject.rootDirectory))

    def _on_add_favorite(self, event):
        root_dir = self.active_tab.listObject.rootDirectory
        initial_row = {"name": os.path.basename(root_dir), "path": root_dir, "key": ""}
        edit_event = viewkit.presets.keyValueSetting.KeyValueSettingEditEvent([], True, -1, initial_row)
        result = self.showSubWindow(views.favoriteDirectory.FavoriteDirectoryEditWindow, _("登録内容の入力"), edit_event)
        if result.code == wx.ID_CANCEL:
            return
        name, path, key = result.user_object["name"], result.user_object["path"], result.user_object["key"]

        if name in self.app.favorite_directory:
            dlg = wx.MessageDialog(
                self,
                _("この名前は既に登録されています。登録を上書きしますか？"),
                _("上書き確認"),
                wx.YES_NO | wx.ICON_QUESTION)
            ret = dlg.ShowModal()
            dlg.Destroy()
            if ret == wx.ID_NO:
                return
        v = dict(self.app.favorite_directory.keyMap.items())
        v[name] = key
        if not views.key_value_setting.validate_key_settings(dict(self.app.favorite_directory.keyMap.items()), v):
            return

        self.app.favorite_directory.add(name, path, key)
        self.update_user_command()

    def _on_setting_favorite(self, event):
        config = views.favoriteDirectory.create_config(self.app.favorite_directory.paramMap, self.app.favorite_directory.keyMap)
        result = self.showSubWindow(views.favoriteDirectory.FavoriteDirectoryWindow, _("お気に入りディレクトリの設定"), config)
        if result.code == wx.ID_CANCEL:
            return
        params, keys = views.favoriteDirectory.split_rows(result.user_object)
        self.app.favorite_directory.replace(params, keys)
        self.update_user_command()

    def _on_setting_open_here(self, event):
        config = views.openHere.create_config(self.app.open_here_command.paramMap, self.app.open_here_command.keyMap)
        result = self.showSubWindow(views.openHere.OpenHereWindow, _("「ここで開く」コマンドの設定"), config)
        if result.code == wx.ID_CANCEL:
            return
        params, keys = views.openHere.split_rows(result.user_object)
        self.app.open_here_command.replace(params, keys)
        self.update_user_command()

    def _on_compress(self, event):
        """選択中のファイル・フォルダを圧縮する"""
        sources = self._get_archive_targets()
        if not sources:
            return
        parameters = views.compress.CompressParameters(sources, self.active_tab.listObject.rootDirectory)
        result = self.showSubWindow(views.compress.CompressWindow, _("圧縮"), parameters)
        if result.code == wx.ID_CANCEL:
            return
        self.operations.add(operation_manager.CompressOperation(result.user_object))

    def _on_extract(self, event):
        """選択中の書庫を解凍する"""
        archives = self._get_archive_targets()
        if not archives:
            return
        for path in archives:
            reason = archiver.check_extractable(path)
            if reason:
                dialog(_("エラー"), reason)
                return
        result = self.showSubWindow(views.extract.ExtractWindow, _("解凍"), self.active_tab.listObject.rootDirectory)
        if result.code == wx.ID_CANCEL:
            return
        for path in archives:
            self.operations.add(operation_manager.ExtractOperation(path, result.user_object))

    def _get_archive_targets(self):
        """圧縮・解凍の対象として、選択中のファイル・フォルダのパスを返す"""
        # ほかのタブでは menuBlocker で無効にしている
        if not isinstance(self.active_tab, tabs.fileList.FileListTab):
            return []
        return [e.fullpath for e in self.active_tab.GetSelectedItems() if isinstance(e, browsableObjects.File)]

    def _on_hash_calc(self, event):
        self.showSubWindow(views.makeHash.MakeHashWindow, _("ファイルハッシュの計算"), self.active_tab.GetFocusedElement().fullpath)

    def _on_exec_program(self, event):
        value = self.input_text(_("ファイル名を指定して実行"), _("コマンドライン"))
        if value is None:
            return
        self.active_tab.ExecProgram(value)

    def _on_add_path(self, event):
        paths = self.active_tab.GetSelectedItems().GetItemPaths()
        if misc.addPath(paths):
            dialog(_("パスの追加"), _("ユーザ環境変数PATHに追加しました。"))
        else:
            dialog(_("パスの追加"), _("追加に失敗しました。"))

    def _on_eject_drive(self, event):
        ret = deviceCtrl.ejectDrive(self.active_tab.GetFocusedElement().letter)
        if ret == errorCodes.OK:
            dialog(_("成功"), _("ドライブは安全に切断されました。"))
            self.update_file_list(False)
        elif ret == errorCodes.FILE_NOT_FOUND:
            dialog(_("エラー"), _("指定されたドライブが見つかりません。既に取り外しされた可能性があります。"))
        elif ret == errorCodes.UNKNOWN:
            # エラー表示はむこうでやってる
            pass
        elif ret == errorCodes.ACCESS_DENIED:
            dialog(_("エラー"), _("取り外しに失敗しました。") + _("このドライブは使用中の可能性があります。"))

    def _on_eject_device(self, event):
        ret = deviceCtrl.EjectDevice(self.active_tab.GetFocusedElement().letter)
        if ret == errorCodes.OK:
            dialog(_("成功"), _("デバイスは安全に取り外せる状態になりました。"))
            self.update_file_list(False)
        elif ret == errorCodes.UNKNOWN:
            dialog(_("エラー"), _("デバイスの取り外しに失敗しました。"))

    def _sort_next(self):
        """sortNext アクションを実行。"""
        if self.active_tab.SortNext() == errorCodes.NOT_SUPPORTED:
            dialog(_("エラー"), _("このオペレーションはサポートされていません。"))

    def _on_drive_info(self, event):
        elem = self.active_tab.GetRootObject()
        if elem is None:
            dialog(_("エラー"), _("ドライブ情報の取得に失敗しました。"))
            return
        self.show_detail(elem)

    def _toggle_extension(self):
        """ファイル名の拡張子の非表示/表示を切り替え、開いているすべてのタブに反映する"""
        hide = not self.app.settings.get_bool("view", "hide_extension", False)
        self.app.settings.set("view", "hide_extension", hide)
        for tab in self.tabs:
            tab.hListCtrl.Refresh()
        self.app.say(_("拡張子を非表示") if hide else _("拡張子を表示"), interrupt=True)

    def _on_regist_original_association(self, event):
        config = views.registerOriginalAssociation.create_config(self.app.settings.get_section("originalAssociation"))
        result = self.showSubWindow(views.registerOriginalAssociation.OriginalAssociationWindow, _("拡張子の独自関連付け"), config)
        if result.code == wx.ID_CANCEL:
            return
        self.app.settings.replace_section("originalAssociation", views.registerOriginalAssociation.rows_to_dict(result.user_object))

    def _on_key_config(self, event):
        keys = self.menu.keymap.key_strings
        rows = []
        for ref_name in defaultKeymap.defaultKeymap[KEYMAP_IDENTIFIER.upper()].keys():
            rows.append({
                "name": menuItemsDic.dic[ref_name],
                "key": keys.get(ref_name, views.key_value_setting.NO_KEY),
                "identifier": ref_name,
            })
        parameters = views.globalKeyConfig.GlobalKeyConfigParameters(rows)
        result = self.showSubWindow(views.globalKeyConfig.GlobalKeyConfigWindow, _("ショートカットキーの設定"), parameters)
        if result.code == wx.ID_CANCEL:
            return

        # キーマップの既存設定を置き換える
        shortcuts = dict(self.app.ctx.settings.getShortcutSettings())
        for row in result.user_object:
            shortcuts[row["identifier"]] = row["key"] if row["key"] != views.key_value_setting.NO_KEY else ""
        self.app.ctx.settings.changeSetting("shortcuts", shortcuts)
        self.app.save_settings()

        # ショートカットキーの変更適用とメニューバーの再描画
        self.update_user_command()

    def _on_font_test(self, event):
        views.fonttest.show_font_test(self)

    def _on_settings(self, event):
        self.showSubWindow(views.settingsDialog.SettingsWindow, _("設定"))

    def _on_search(self, event):
        base_path = self.active_tab.listObject.rootDirectory
        out_lst = []  # 入力画面が出てるときに、もうファイルリスト取得を開始してしまう
        task = workerThreads.RegisterTask(workerThreadTasks.GetRecursiveFileList, {'path': base_path, 'out_lst': out_lst, 'eol': True})

        history_count = self.app.settings.get_int("search", "history_count", 0, 0, 100)
        search_history = history.History(history_count, False)
        grep_history = history.History(history_count, False)
        hist = {}
        try:
            with open(constants.HISTORY_FILE_NAME, 'rb') as f:
                hist = pickle.load(f)
                search_history.lst = hist["search"]
                search_history.cursor = len(hist["search"]) - 1
                grep_history.lst = hist["grep"]
                grep_history.cursor = len(hist["grep"]) - 1
        except BaseException:
            pass

        parameters = views.search.SearchParameters(base_path, list(reversed(search_history.getList())), list(reversed(grep_history.getList())))
        result = self.showSubWindow(views.search.SearchWindow, _("検索"), parameters)
        if result.code == wx.ID_CANCEL:
            task.Cancel()
            return
        val = result.user_object

        target = {
            'action': "search" if val['type'] == 0 else "grep",
            'basePath': base_path,
            'out_lst': out_lst,
            'keyword': val['keyword'],
            'isRegularExpression': val['isRegularExpression']}
        self.navigate(target, as_new_tab=True)

        if val['type'] == 0:
            search_history.add(val['keyword'])
        else:
            grep_history.add(val['keyword'])
        hist["search"] = search_history.getList()
        hist["grep"] = grep_history.getList()
        try:
            with open(constants.HISTORY_FILE_NAME, 'wb') as f:
                pickle.dump(hist, f)
        except BaseException:
            pass

    def _add_link_detail(self, detail, path):
        """シンボリックリンクやジャンクションの場合に、種類とリンク先を詳細情報に追加する。"""
        try:
            link = reparse_link.get_link(path)
        except OSError as err:
            self.log.warning("Cannot read link target of %s (%s)" % (path, err))
            detail.add(_("リンク先"), _("不明"))
            return
        if link is None:
            return
        detail.add(_("リンクの種類"), reparse_link.get_kind_name(link.kind))
        detail.add(_("リンク先"), link.target)
        absolute = reparse_link.get_absolute_target(path, link)
        if os.path.normcase(absolute) != os.path.normcase(os.path.normpath(link.target)):
            detail.add(_("リンク先の絶対パス"), absolute)
        if not os.path.exists(path):
            detail.add(_("リンクの状態"), _("リンク先が見つかりません"))

    def show_detail(self, elem):
        d = views.objectDetail.ObjectDetailParameters()
        d.add(_("名前"), elem.basename)
        d.add(_("パス"), elem.fullpath)
        if isinstance(elem, browsableObjects.File) or isinstance(elem, browsableObjects.Stream):
            if elem.size >= 0:
                d.add(_("サイズ"), misc.ConvertBytesTo(elem.size, misc.UNIT_AUTO, True))
                d.add(_("サイズ(バイト)"), elem.size)
                if isinstance(elem, browsableObjects.Folder):
                    d.add(_("内容"), _("ファイル数： %(files)d サブディレクトリ数： %(dirs)d") % {"files": elem.fileCount, "dirs": elem.dirCount})
            elif isinstance(elem, browsableObjects.Folder):
                d.add(_("サイズ"), views.objectDetail.CALCURATING)
                d.add(_("サイズ(バイト)"), views.objectDetail.CALCURATING)
                d.add(_("内容"), views.objectDetail.CALCURATING)
                d.dir_calc_path = elem.fullpath
        if isinstance(elem, browsableObjects.File):
            d.add(_("作成日時"), elem.creationDate.strftime("%Y/%m/%d(%a) %H:%M:%S"))
            d.add(_("更新日時"), elem.modDate.strftime("%Y/%m/%d(%a) %H:%M:%S"))
            d.add(_("属性"), elem.longAttributesString)
            d.add(_("種類"), elem.typeString)
            if not elem.shortName == "":
                d.add(_("短い名前"), elem.shortName)
            else:
                d.add(_("短い名前"), _("なし"))

            self._add_link_detail(d, elem.fullpath)

            try:
                h = win32file.CreateFile(
                    elem.fullpath,
                    0,
                    win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                    None,
                    win32file.OPEN_EXISTING,
                    win32file.FILE_FLAG_BACKUP_SEMANTICS,  # これがないとディレクトリを開けない
                    0)
                info = win32file.GetFileInformationByHandleEx(h, win32file.FileStandardInfo)
            except win32file.error as err:  # リンク先が存在しない場合など
                self.log.warning("Cannot get file information of %s (%s)" % (elem.fullpath, err))
                info = None
            if info:
                d.add(_("消費ディスク領域"),
                      misc.ConvertBytesTo(info["AllocationSize"], misc.UNIT_AUTO, True) + " (" + str(info["AllocationSize"]) + " bytes)")
                tmp = ""
                if info["DeletePending"]:
                    tmp += _("削除予約済 ")
                if info["NumberOfLinks"] > 1:
                    tmp += _("ハードリンクにより他の %d 箇所から参照" % (info["NumberOfLinks"] - 1))
                if tmp == "":
                    tmp = _("なし")
                d.add(_("追加情報"), tmp)

        if isinstance(elem, browsableObjects.Drive):
            if elem.free >= 0:
                d.add(_("フォーマット"), fileSystemManager.GetFileSystemObject(elem.letter))
                if elem.total > 0:
                    d.add(_("空き容量"), "%s (%s%%)" % (misc.ConvertBytesTo(elem.free, misc.UNIT_AUTO, True), elem.free * 100 // elem.total))
                else:
                    d.add(_("空き容量"), misc.ConvertBytesTo(elem.free, misc.UNIT_AUTO, True))
                d.add(_("総容量"), misc.ConvertBytesTo(elem.total, misc.UNIT_AUTO, True))
            else:
                d.add(_("フォーマット"), _("未挿入"))
            d.add(_("種類"), elem.typeString)
        if isinstance(elem, browsableObjects.NetworkResource) and elem.address != "":
            d.add(_("IPアドレス"), elem.address)
        if isinstance(elem, browsableObjects.File) and shortcut_link.is_shortcut(elem.fullpath):
            d.shortcut_path = elem.fullpath
        result = self.showSubWindow(views.objectDetail.ObjectDetailWindow, _("詳細情報"), d)
        # ショートカットの設定を変えると更新日時が変わるので、一覧を更新する
        if getattr(result, "user_object", None) is True and hasattr(self.active_tab, "UpdateFilelist"):
            self.active_tab.UpdateFilelist(silence=True)


class FalconMenu:
    """
    falcon独自のショートカットキー(keymap)と、メニュー項目の有効・無効を管理する。
    ショートカットキーはviewkitの設定ファイルの shortcuts に保存する。
    """

    def __init__(self, window: MainWindow, identifier: str):
        self.window = window
        self.identifier = identifier
        self.log = getLogger("%s.menu" % constants.LOG_PREFIX)
        self.menu_bar = None
        self.disabled_items = set()  # 無効にしたメニューのref

        self.disabled_menu_bar = None  # ショートカット無効状態の時に表示するダミーのメニューバー

        self.init_shortcut()

    def init_shortcut(self):
        """設定ファイルからショートカットキーを読み込む"""
        settings = self.window.app_ctx.settings
        shortcuts = settings.getShortcutSettings()
        if not shortcuts:
            # 初回起動
            shortcuts = dict(defaultKeymap.defaultKeymap[self.identifier.upper()])
            settings.changeSetting("shortcuts", shortcuts)
            settings.save()
        self.keymap = keymap.Keymap(keymap.create_main_window_filter())
        self.keymap.load(shortcuts)
        errors = self.keymap.pop_errors()
        if errors:
            message = _("設定されたショートカットキーが正しくありません。キーの重複、存在しないキー名の指定、使用できないキーパターンの指定などが考えられます。以下のキーの設定内容をご確認ください。\n\n")
            for v in errors:
                message += v + "\n"
            dialog(_("エラー"), message)

    def apply_shortcut(self, window):
        """指定されたウィンドウに、ショートカットキーを登録する"""
        self.keymap.apply(window)

    def get_key_string(self, identifier):
        return self.keymap.get_key_string(identifier)

    def set_menu_bar(self, menu_bar):
        self.menu_bar = menu_bar
        self._create_disabled_menu_bar()
        for ref in self.disabled_items:
            if menu_bar.FindItemById(ref) is not None:
                menu_bar.Enable(ref, False)

    def _create_disabled_menu_bar(self):
        """
        ショートカット無効状態の時に表示する、操作できないメニューバーを作る。
        名前の変更中に一覧の大きさが変わると、編集が打ち切られてしまう。
        幅の狭いウィンドウではメニューバーが折り返されるため、同じ見出しを並べて高さをそろえる。
        """
        if self.disabled_menu_bar is not None and not self.disabled_menu_bar.IsAttached():
            self.disabled_menu_bar.Destroy()
        self.disabled_menu_bar = wx.MenuBar()
        for dummy, title in self.menu_bar.GetMenus():
            menu = wx.Menu()
            menu.Append(wx.ID_ANY, _("現在メニューは操作できません")).Enable(False)
            self.disabled_menu_bar.Append(menu, title)

    def _to_ref(self, identifier):
        return identifier if isinstance(identifier, int) else menuItemsStore.getRef(identifier)

    def enable(self, identifier, enable=True):
        """メニューの有効・無効を切り替える。identifierは識別子(str)またはref(int)"""
        ref = self._to_ref(identifier)
        if enable:
            self.disabled_items.discard(ref)
        else:
            self.disabled_items.add(ref)
        if self.menu_bar is not None and self.menu_bar.FindItemById(ref) is not None:
            self.menu_bar.Enable(ref, enable)

    def is_enable(self, identifier):
        return self._to_ref(identifier) not in self.disabled_items

    def register_menu_command(self, menu, identifiers):
        """コンテキストメニューなどに、メニュー項目をショートカットキーの表示付きで追加する"""
        for identifier in identifiers:
            if identifier == "":
                menu.AppendSeparator()
                continue
            title = menuItemsDic.dic[identifier]
            shortcut = self.get_key_string(identifier)
            label = title if shortcut is None else "%s\t%s" % (title, shortcut)
            menu.Append(menuItemsStore.getRef(identifier), label)
