# -*- coding: utf-8 -*-
# Falcon past progress tab
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
コピー/貼り付けの進捗状況を表示するタブ。
"""

import datetime
import os
import wx

import browsableObjects
import errorCodes
import globalVars
import misc
import StringUtil
import tabs
import views.OperationSelecter
import simpleDialog

from . import base


class PastProgressTab(base.FalconTabBase):
    def Initialize(self, parent, creator, existing_listctrl=None):
        super().Initialize(parent, creator, existing_listctrl)

    def SetFileOperator(self, operator):
        """ファイルオペレーターを設定して、オペレーション終了時のコールバックを登録する。"""
        self.fileOperator = operator
        operator.SetCallback("finished", self.OnOperationFinish)
        operator.SetCallback("setPercentage", self.OnPercentageSet)
        operator.SetCallback("confirm", self.OnConfirm)
        # パーセンテージのコールバックが来るのは、次にパーセンテージが変化するときだけである。なので、現時点でのパーセンテージは、このタイミングで手動で得ておく。
        self.OnPercentageSet(operator, {})
        # 確認項目を最新にしておく
        self._refresh()

    def _refresh(self):
        """確認待ちとエラーの項目を、一覧に反映する。"""
        failed = self.fileOperator.CheckFailed()
        self.listObject.Update(self.fileOperator.GetConfirmationManager(), failed)
        if self.fileOperator.CheckFinished():
            waiting = self.listObject.GetUnresolvedCount() - len(failed)
            if waiting > 0:
                self.listObject.GetHeaderObject().set_status(_("確認待ち"), _("%(count)d件の確認が必要です") % {"count": waiting})
            elif failed:
                self.listObject.GetHeaderObject().set_status(_("エラー"), _("%(count)d件を処理できませんでした") % {"count": len(failed)})
            else:
                self.listObject.SetHeaderPercentage(100)
        # 確認やエラーがあれば、その先頭にカーソルを置く
        self.Update(self.listObject, 1 if self.listObject.GetUnresolvedCount() > 0 else 0)

    def OnOperationFinish(self, op, parameters):
        self._refresh()
        if self.listObject.GetUnresolvedCount() == 0:
            globalVars.app.main_window.close_tab(self)

    def OnPercentageSet(self, op, parameters):
        self.listObject.SetHeaderPercentage(op.GetPercentage())
        # リストの要素は browsableObject そのものなので、再描画だけでよい
        self.hListCtrl.RefreshItem(0)

    def OnConfirm(self, op, parameters):
        self._refresh()

    def OpenContextMenu(self, event):
        m = wx.Menu()
        m.Append(0, _("詳細を表示"))
        item = self.hListCtrl.GetPopupMenuSelectionFromUser(m)
        m.Destroy()
        if item < 0:
            return
        self.handleDetails()

    def handleDetails(self):
        elem = self.GetFocusedElement()
        if elem is None or isinstance(elem, (browsableObjects.PastProgressHeader, browsableObjects.PastProgressFailedItem)):
            return  # 確認が必要な項目ではない
        index = elem.getConfirmationManagerIndex()
        confs = self.fileOperator.GetConfirmationManager()
        confirmElem = confs.GetAt(index)
        e = confirmElem.GetElement()
        from_path = e.path
        dest_path = e.destpath
        try:
            # リンク先がないリンクの場合は、リンク自体の情報を使う
            from_stat = os.stat(from_path) if os.path.exists(from_path) else os.lstat(from_path)
            dest_stat = os.stat(dest_path) if os.path.exists(dest_path) else os.lstat(dest_path)
        except OSError as err:
            simpleDialog.dialog(_("エラー"), err.strerror)
            return
        info = [
            (_("名前"), os.path.basename(from_path), "", ""), (_("サイズ"), misc.ConvertBytesTo(
                dest_stat.st_size, misc.UNIT_AUTO, True), "→", misc.ConvertBytesTo(
                from_stat.st_size, misc.UNIT_AUTO, True)), (_("更新日時"), datetime.datetime.fromtimestamp(
                    dest_stat.st_mtime), "→", datetime.datetime.fromtimestamp(
                    from_stat.st_mtime))]
        result = globalVars.app.main_window.showSubWindow(
            views.OperationSelecter.OperationSelecterWindow, _("ファイル操作確認"),
            views.OperationSelecter.OperationSelecterParameters(_("上書きしますか？"), info, views.OperationSelecter.GetMethod("ALREADY_EXISTS"), False))
        if result.code != wx.ID_OK:
            return
        val = result.user_object
        if val['all'] is True:  # 「以降も同様に処理」がオン
            confs.RespondAll(confirmElem, val['response'])
        else:  # この1件だけ
            confirmElem.Respond(val['response'])  # 渓谷に対して、文字列でレスポンスする
        # end これ以降全てかこれだけか
        self.fileOperator.UpdateConfirmation()  # これで繁栄する
        instructions = self.fileOperator.instructions
        directories = {os.path.dirname(source) for source, dummy in instructions["target"]}
        directories.add(instructions["to"])
        directories.update(os.path.dirname(destination) for dummy, destination in instructions["target"])
        self.fileOperator.Execute()  # これでコピーを再実行
        globalVars.app.main_window.update_file_lists(directories)

    def GoForward(self, stream, admin=False):
        self.handleDetails()

    def ReadCurrentFolder(self):
        globalVars.app.say(_("貼り付けの結果を閲覧中"))

    def ReadListItemNumber(self, short=False):
        globalVars.app.say(_("項目数 %(results)d件") %
                           {'results': len(self.listObject)}, interrupt=True)

    def GetTabName(self):
        """タブコントロールに表示する名前"""
        destination = self.fileOperator.instructions["to"]
        word = _("%(destination)sへの貼り付け") % {"destination": os.path.basename(destination) or destination}
        word = StringUtil.GetLimitedString(
            word, globalVars.app.settings.get_int("view", "header_title_length", 20, 1))
        return word

    def DeleteAllItems(self):
        super().DeleteAllItems()

    def OnLabelEditStart(self, evt):
        pass

    def OnLabelEditEnd(self, evt):
        pass
