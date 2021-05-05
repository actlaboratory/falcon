# -*- coding: utf-8 -*-
# Falcon stream list tab
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
副ストリームのリストです。
"""

import os
import wx
import clipboard
import errorCodes
import lists
import browsableObjects
import globalVars
import fileOperator
import misc
import workerThreads
import workerThreadTasks
import fileSystemManager
from tabs.driveList import *
import StringUtil

from simpleDialog import *
from . import base


class StreamListTab(base.FalconTabBase):
    """副ストリームリストが表示されているタブ。"""

    def OnLabelEditEnd(self, evt):
        self.isRenaming = False
        self.parent.SetShortcutEnabled(True)
        if evt.IsEditCancelled():  # ユーザによる編集キャンセル
            return
        e = self.hListCtrl.GetEditControl()
        f = self.listObject.GetElement(self.GetFocusedItem())
        if error:
            dialog(_("エラー"), error)
            evt.Veto()
            return
        inst = {"operation": "rename", "files": [f.fullpath], "to": [newName]}
        op = fileOperator.FileOperator(inst)
        ret = op.Execute()
        if op.CheckSucceeded() == 0:
            dialog(_("エラー"), _("名前が変更できません。"))
            evt.Veto()
            return
        # end fail
        f.basename = e.GetLineText(0)
        f.fullpath = f.file + f.basename
    # end onLabelEditEnd

    def FileOperationTest(self):
        if self.task:
            self.task.Cancel()
        else:
            self.task = workerThreads.RegisterTask(workerThreadTasks.DebugBeep)

    def Trash(self):
        focus_index = self.GetFocusedItem()
        paths = self.listObject.GetItemPaths()  # パスのリストを取っておく
        target = []
        for elem in self.GetSelectedItems():
            target.append(elem.fullpath)
        # end for
        if len(target) == 1:
            msg = _("%(file)s\nこのファイルをごみ箱に移動してもよろしいですか？") % {'file': target[0]}
        else:
            msg = _("選択中の項目 %(num)d件をごみ箱に移動してもよろしいですか？") % {'num': len(target)}
        # end メッセージどっちにするか
        dlg = wx.MessageDialog(
            None, msg, _("確認"), wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_NO:
            return
        inst = {"operation": "trash", "target": target}
        op = fileOperator.FileOperator(inst)
        ret = op.Execute()
        print("succeeded %s" % op.CheckSucceeded())
        if op.CheckSucceeded() == 0:
            dialog(_("エラー"), _("ファイルをゴミ箱に移動できませんでした。"))
            return
        # end error
        failed = op.CheckFailed()
        print("fail %d" % len(failed))
        self.UpdateFilelist(silence=True)
        # カーソルをどこに動かすかを決定、まずはもともとフォーカスしてた項目があるかどうか
        if os.path.exists(paths[focus_index]):
            new_cursor_path = paths[focus_index]  # フォーカスしてたファイル
        else:  # あるファイルを上下に探索
            new_cursor_path = ""
            ln = len(paths)
            i = 1
            while(True):
                if i > focus_index and i > ln - focus_index - 1:
                    break  # 探索し尽くしたらやめる
                tmp = focus_index - i
                if tmp >= 0 and os.path.exists(paths[tmp]):  # あった
                    new_cursor_path = paths[tmp]
                    break
                # end 上
                tmp = focus_index + i
                if tmp >= ln and os.path.exists(paths[tmp]):  # あった
                    new_cursor_path = paths[tmp]
                    break
                # end 下
                i += 1
            # end 探索
        # end さっきフォーカスしてた項目がなくなってた
        # カーソルをどの項目に動かすか分かった
        focus_index = 0
        for elem in self.listObject:
            if elem.fullpath == new_cursor_path:
                break
            focus_index += 1
        # end 検索
        self.hListCtrl.Focus(focus_index)

    def Delete(self):
        focus_index = self.GetFocusedItem()
        paths = self.listObject.GetItemPaths()  # パスのリストを取っておく
        target = []
        for elem in self.GetSelectedItems():
            target.append(elem.fullpath)
        # end for
        if len(target) == 1:
            msg = _("%(file)s\nこのファイルを完全削除してもよろしいですか？") % {'file': target[0]}
        else:
            msg = _("選択中の項目 %(num)d件を完全削除してもよろしいですか？") % {'num': len(target)}
        # end メッセージどっちにするか
        dlg = wx.MessageDialog(
            None,
            msg,
            _("完全削除の確認"),
            wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_NO:
            return
        inst = {"operation": "delete", "target": target}
        op = fileOperator.FileOperator(inst)
        ret = op.Execute()
        if op.CheckSucceeded() == 0:
            dialog(_("エラー"), _("削除に失敗しました。"))
            return
        # end error
        self.UpdateFilelist(silence=True)
        focus_index = self._findFocusAfterDeletion(paths, focus_index)
        self.Focus(focus_index)

    def Copy(self):
        if not self.IsItemSelected():
            return
        globalVars.app.say(_("コピー"))
        c = clipboard.ClipboardFile()
        c.SetFileList(self.GetSelectedItems().GetItemPaths())
        c.SendToClipboard()

    def Cut(self):
        if not self.IsItemSelected():
            return
        globalVars.app.say(_("切り取り"))
        c = clipboard.ClipboardFile()
        c.SetOperation(clipboard.MOVE)
        c.SetFileList(self.GetSelectedItems().GetItemPaths())
        c.SendToClipboard()

    def BeginDrag(self, event):
        return errorCodes.NOT_SUPPORTED  # 基底クラスではなにも許可しない

    def MarkSet(self):
        return errorCodes.NOT_SUPPORTED  # 基底クラスではなにも許可しない

    def ReadCurrentFolder(self):
        curdir = os.path.basename(self.listObject.rootDirectory)
        drive = os.path.splitdrive(self.listObject.rootDirectory)[0]
        if self.listObject.rootDirectory[0] != "\\":
            s = _("現在は、ドライブ%(drive)sの %(folder)s") % {
                'drive': drive[0], 'folder': curdir if curdir != "" else "ルート"}
        else:
            s = _("現在は、%(drive)sの %(folder)s") % {
                'drive': drive, 'folder': curdir if curdir != "" else "ルート"}
        globalVars.app.say(s, interrupt=True)

    def ReadListItemNumber(self, short=False):
        streams = len(self.listObject)
        if short:
            globalVars.app.say(_("ストリーム数 %(streams)d") % {'streams': streams})
            return
        # end short
        curdir = os.path.basename(self.listObject.rootDirectory)
        if curdir == "":
            if len(self.listObject.rootDirectory) <= 3:
                curdir = _("%(letter)sルート") % {
                    'letter': self.listObject.rootDirectory[0]}
            else:  # ネットワークルート
                curdir = self.listObject.rootDirectory
        globalVars.app.say(
            _("%(containing)sには、ストリーム %(streams)d個") % {
                'containing': curdir,
                'streams': streams},
            interrupt=True)

    def ReadListInfo(self):
        tmp = self.listObject.rootDirectory.split("\\")
        curdir = os.path.basename(self.listObject.rootDirectory)
        if curdir == "":
            if len(self.listObject.rootDirectory) <= 3:
                curdir = _("%(letter)sルート") % {
                    'letter': self.listObject.rootDirectory[0]}
            else:  # ネットワークルート
                curdir = self.listObject.rootDirectory
        globalVars.app.say(
            _("%(dir)sに含まれるストリームを %(sortkind)sの%(sortad)sで一覧中、 %(max)d個中 %(current)d個目") % {
                'dir': curdir,
                'sortkind': self.listObject.GetSortKindString(),
                'sortad': self.listObject.GetSortAdString(),
                'max': len(
                    self.listObject),
                'current': self.GetFocusedItem() + 1},
            interrupt=True)

    def GetTabName(self):
        """タブコントロールに表示する名前"""
        word = os.path.basename(self.listObject.rootDirectory)
        if word == "":  # ルート
            word = self.listObject.rootDirectory
        word = StringUtil.GetLimitedString(
            word, globalVars.app.config["view"]["header_title_length"])
        return word

    def GetRootObject(self):
        """ドライブ詳細情報表示で用いる"""
        return misc.GetRootObject(self.listObject.rootDirectory)
