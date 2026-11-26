# -*- coding: utf-8 -*-
# Falcon search result tab common functions
# Note: All comments except these top lines will be written in Japanese.

"""
ファイル名検索・ファイル内容検索のタブに共通の処理。
tabs/searchResultTabBase.py は他のプロジェクトと共通のため変更せず、ここで不具合を直す。
"""

import datetime
import os

import win32file

import globalVars
import workerThreads
import workerThreadTasks

from . import searchResultTabBase


def _path_key(path):
    """パスを比べるための文字列を返す。大文字・小文字の違いをなくし、末尾を区切り文字にそろえる。"""
    return os.path.join(os.path.normcase(path), "")


class SearchResultTabCommon(searchResultTabBase.SearchResultTabBase):
    """SearchResultTabBase の不具合を直した、検索結果のタブの共通部分。"""

    def __init__(self, environment):
        super().__init__(environment)
        self.list_task = None  # ファイル一覧を取得するタスク

    def StartSearch(self, rootPath, searches, keyword, isRegularExpression, list_task=None):
        """
        検索を始める。list_task には、searches にファイル一覧を入れているタスクを渡す。タブを閉じたときに止める。
        SearchResultTabBase では、検索条件が2回読み上げられていたため、表示用のリストは読み上げないようにする。
        """
        self.list_task = list_task
        self.listObject = self.listType()
        self.listObject.Initialize(rootPath, searches, keyword, isRegularExpression, True)
        self.tempListObject = self.listType()
        self.tempListObject.Initialize(rootPath, searches, keyword, isRegularExpression)
        self.SetListColumns(self.listObject)
        self._InitIconList()
        self.taskState = workerThreads.RegisterTask(
            workerThreadTasks.PerformSearch, {
                "listObject": self.tempListObject,
                "tabObject": self
            }
        )

        # タブの名前変更を通知
        globalVars.app.main_window.update_tab_name()

    def UpdateFilelist(self, silence=False, cursorTargetName=""):
        """
        同じ条件で検索をやり直す。ファイルは非同期処理で増えるので、cursorTargetNameは使用されない。
        silence=True のとき（ショートカットの作成などのファイル操作の後）は再検索せず、
        カーソル位置の項目の情報だけを最新にする。
        SearchResultTabBase では、未定義の変数を参照して例外になり、再検索できなかった。
        """
        if silence:
            self._refresh_focused_element()
            return
        if not self.tempListObject.GetFinishedStatus():
            globalVars.app.say(_("現在検索中です。再検索はできません。"), interrupt=True)
            return
        # end まだ検索終わってない
        globalVars.app.say(_("再検索"), interrupt=True)
        self.DeleteAllItems()
        searches = []
        self.listObject.RedoSearch(searches)
        self.list_task = workerThreads.RegisterTask(
            workerThreadTasks.GetRecursiveFileList, {
                "path": self.listObject.rootDirectory, "out_lst": searches, "eol": True})
        self.tempListObject = self.listType()
        self.tempListObject.Initialize(
            self.listObject.rootDirectory,
            searches,
            self.listObject.GetKeywordString(),
            self.listObject.is_regular_expression,
            True)
        self.taskState = workerThreads.RegisterTask(workerThreadTasks.PerformSearch, {
            "listObject": self.tempListObject, "tabObject": self})

    def _refresh_focused_element(self):
        """カーソル位置の項目のサイズ・日時・属性を読み直す。なくなっていれば一覧から取り除く。"""
        focused = self.GetFocusedElement()
        if focused is None:
            return
        if not os.path.lexists(focused.fullpath):
            self.remove_deleted_items([focused.fullpath])
            return
        key = _path_key(focused.fullpath)
        try:
            for element in self.listObject.GetItemList():
                if _path_key(element.fullpath) == key:
                    self._reload_element_info(element)
        except OSError as err:
            self.log.warning("Cannot reload %s (%s)" % (focused.fullpath, err))
        self.hListCtrl.Refresh()

    def _reload_element_info(self, element):
        """項目のサイズ・日時・属性を、ファイルから読み直す。フォルダのサイズは変えない。"""
        stat = os.stat(element.fullpath)
        if element.size >= 0 and not os.path.isdir(element.fullpath):
            element.size = stat.st_size
        # 範囲外の日時は、一覧を作るときと同じく 0 にする
        mtime = stat.st_mtime if stat.st_mtime <= 32536799999 else 0
        ctime = stat.st_ctime if stat.st_ctime <= 32536799999 else 0
        element.modDate = datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc).astimezone(globalVars.app.timezone)
        element.creationDate = datetime.datetime.fromtimestamp(ctime, datetime.timezone.utc).astimezone(globalVars.app.timezone)
        element.attributes = win32file.GetFileAttributes(element.fullpath)
        element.GetAttributesString()

    def remove_deleted_items(self, deleted_paths):
        """
        deleted_paths とその中の項目のうち、なくなったものを一覧から取り除く。再検索はしない。
        検索中は結果が追加され続けているため、何もしない。
        """
        if not self.tempListObject.GetFinishedStatus():
            return
        prefixes = tuple(_path_key(path) for path in deleted_paths)

        def is_deleted(element):
            return _path_key(element.fullpath).startswith(prefixes) and not os.path.lexists(element.fullpath)

        old_items = list(self.listObject.GetItemList())
        if not any(is_deleted(element) for element in old_items):
            return
        focused = self.GetFocusedElement()
        index = self.GetFocusedItem()
        for elements in self.listObject.lists:
            elements[:] = [element for element in elements if not is_deleted(element)]
        items = list(self.listObject.GetItemList())
        if focused in items:
            cursor = items.index(focused)
        else:
            cursor = min(index, len(items) - 1)
        # 検索結果のアイコンのハンドルは破棄されているので、一覧を作り直さず、登録済みの画像のまま行だけを入れ替える
        self.checkedItem &= set(items)
        self.hListCtrl.set_items(items)
        self.Focus(cursor)

    def OnLabelEditEnd(self, evt):
        """
        名前の変更が終わったら、変更した項目と、その中にある項目のパスを新しい名前に合わせる。再検索はしない。
        ファイル内容検索で同じファイルが複数ヒットしている場合は、そのすべてを変更する。
        """
        renamed = self.listObject.GetElement(self.GetFocusedItem())
        old_path = renamed.fullpath if renamed is not None else ""
        super().OnLabelEditEnd(evt)
        if renamed is None or evt.IsEditCancelled() or not evt.IsAllowed():
            return
        new_path = os.path.join(renamed.directory, renamed.basename)
        if new_path == old_path:
            return
        self._rename_paths(old_path, new_path)
        self.hListCtrl.Refresh()

    def _rename_paths(self, old_path, new_path):
        """一覧の中で、old_path とその中の項目のパスを new_path に置き換える。"""
        old_key = _path_key(old_path)
        for element in self.listObject.GetItemList():
            key = _path_key(element.fullpath)
            if not key.startswith(old_key):
                continue
            if key == old_key:
                fullpath = new_path
                element.basename = os.path.basename(new_path)
            else:
                fullpath = new_path + element.fullpath[len(old_path):]
            element.fullpath = fullpath
            element.directory = os.path.dirname(fullpath)
            if hasattr(element, "relpath"):
                element.relpath = os.path.relpath(fullpath, self.listObject.rootDirectory)

    def OnClose(self):
        """検索とファイル一覧の取得が実行中であれば止める。"""
        if self.list_task is not None and self.list_task.GetFinishState() is not True:
            self.list_task.Cancel()
        super().OnClose()
