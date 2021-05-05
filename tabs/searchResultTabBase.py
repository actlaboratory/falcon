# -*- coding: utf-8 -*-
# Falcon searchResultTabBase
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
	通常検索・ファイル内容検索共通の関数群
"""

import wx

import browsableObjects
import errorCodes
import globalVars
import misc
import StringUtil
import tabs
import workerThreads
import workerThreadTasks


class SearchResultTabBase(tabs.fileList.FileListTab):
    def __init__(self, environment):
        super().__init__(environment)
        self.folderCount = 0

    def StartSearch(self, rootPath, searches, keyword, isRegularExpression):
        self.listObject = self.listType()
        self.listObject.Initialize(
            rootPath, searches, keyword, isRegularExpression)
        self.tempListObject = self.listType()
        self.tempListObject.Initialize(
            rootPath, searches, keyword, isRegularExpression)
        self.SetListColumns(self.listObject)
        self._InitIconList()
        self.taskState = workerThreads.RegisterTask(
            workerThreadTasks.PerformSearch, {
                'listObject': self.tempListObject, 'tabObject': self})

        # タブの名前変更を通知
        globalVars.app.hMainView.UpdateTabName()

    def _onSearchHitCallback(self, hits):
        """コールバックで、ヒットしたオブジェクトのリストが降ってくるので、それをリストビューに追加していく。"""
        globalVars.app.PlaySound("click.ogg")
        for elem in hits:
            if isinstance(elem, browsableObjects.Folder):
                self._AppendElement(elem, self.folderCount)
                self.folderCount += 1
                self.listObject.folders.append(elem)
            else:
                self._AppendElement(elem)
                self.listObject.lists[-1].append(elem)
        # end 追加
        if self.tempListObject.GetFinishedStatus(
        ) and self.hListCtrl.GetItemCount() == len(self.tempListObject):
            # ここはcallAfterで実行されるため、検索修了時点でCallAfterのキューに２つ以上のこの関数が貯まってるとソートが２回発生して画面とリストがずれるので条件を二重にして対策した
            self.ApplySort()

    def UpdateFilelist(self, silence=False, cursorTargetName=""):
        """検索をやり直す。ファイルは非同期処理で増えるので、cursorTargetNameは使用されない。"""
        if not self.tempListObject.GetFinishedStatus():
            globalVars.app.say(_("現在検索中です。再建策はできません。"), interrupt=True)
            return
        # end まだ検索終わってない
        if not silence:
            globalVars.app.say(_("再建策"), interrupt=True)
        # end not silence
        self.DeleteAllItems()
        self.listObject.RedoSearch()
        workerThreads.RegisterTask(
            workerThreadTasks.PerformSearch, {
                'listObject': self.listObject, 'tabObject': self})

    def GoForward(self, stream, admin=False):
        """検索結果表示では、フォルダを開くときに別タブを生成する。"""
        index = self.GetFocusedItem()
        elem = self.listObject.GetElement(index)
        if (not stream) and (not isinstance(
                elem, browsableObjects.Folder)):  # このファイルを開く
            misc.RunFile(elem.fullpath, admin)
            return
        else:
            # 新しいタブで開く
            globalVars.app.hMainView.Navigate(elem.fullpath, as_new_tab=True)
        # end ファイルを開くか移動するか
    # end GoForward

    def GoBackward(self):
        return errorCodes.BOUNDARY

    def OpenContextMenu(self, event):
        menu = wx.Menu()
        globalVars.app.hMainView.menu.RegisterMenuCommand(menu, (
            "MOVE_FORWARD",
            "EDIT_FULLPATHCOPY",
            "EDIT_CUT",
            "EDIT_COPY",
            "FILE_RENAME",
            "FILE_CHANGEATTRIBUTE",
            "FILE_MAKESHORTCUT",
            "FILE_TRASH",
            "FILE_DELETE",
            "FILE_VIEW_DETAIL",
            "FILE_SHOWPROPERTIES"
        ))
        globalVars.app.hMainView.PopupMenu(menu)

    def ReadCurrentFolder(self):
        state = _("検索完了") if self.tempListObject.GetFinishedStatus(
        ) is True else _("検索中")
        globalVars.app.say(
            _("キーワード %(keyword)s で ディレクトリ %(dir)s を%(state)s") % {
                'keyword': self.listObject.GetKeywordString(),
                'dir': self.listObject.rootDirectory,
                'state': state},
            interrupt=True)

    def ReadListItemNumber(self, short=False):
        globalVars.app.say(_("検索結果 %(results)d件") %
                           {'results': len(self.listObject)}, interrupt=True)

    def GetTabName(self):
        """タブコントロールに表示する名前"""
        word = self.listObject.GetKeywordString()
        word = StringUtil.GetLimitedString(
            word, globalVars.app.config["view"]["header_title_length"])
        word = _("%(word)sの検索") % {"word": word}
        return word

    def DeleteAllItems(self):
        super().DeleteAllItems()
        self.folderCount = 0

    def OnClose(self):
        """検索の非同期処理が実行中であればキャンセルして、終了を待機する。"""
        super().OnClose()
        if self.taskState.GetFinishState() is not True:
            self.taskState.Cancel(wait=True)
        # end 待つ
    # end OnClose
