# -*- coding: utf-8 -*-
# Falcon search result tab common functions
# Note: All comments except these top lines will be written in Japanese.

"""
ファイル名検索・ファイル内容検索のタブに共通の処理。
tabs/searchResultTabBase.py は他のプロジェクトと共通のため変更せず、ここで不具合を直す。
"""

import globalVars
import workerThreads
import workerThreadTasks

from . import searchResultTabBase


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
        SearchResultTabBase では、未定義の変数を参照して例外になり、再検索できなかった。
        """
        if not self.tempListObject.GetFinishedStatus():
            globalVars.app.say(_("現在検索中です。再検索はできません。"), interrupt=True)
            return
        # end まだ検索終わってない
        if not silence:
            globalVars.app.say(_("再検索"), interrupt=True)
        # end not silence
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

    def OnClose(self):
        """検索とファイル一覧の取得が実行中であれば止める。"""
        if self.list_task is not None and self.list_task.GetFinishState() is not True:
            self.list_task.Cancel()
        super().OnClose()
