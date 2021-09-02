# -*- coding: utf-8 -*-
# Falcon main list tab
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
ファイルリストやドライブ一覧リストなどです。一通りのファイル操作を行うことができます。
"""

import datetime
import os
import time
import wx

import browsableObjects
import clipboard
import constants
import errorCodes
import fileOperator
import fileSystemManager
import globalVars
import lists
import misc
import StringUtil
import tabs.streamList
import views.OperationSelecter
import views.newNameForPast
import workerThreads
import workerThreadTasks


from simpleDialog import *
from . import base


class FileListTab(base.FalconTabBase):
    """ファイル/フォルダリストが表示されているタブ。"""

    def OnLabelEditEnd(self, evt):
        """
                ファイル名変更の入力終了イベント
                入力中にリストが並び替えされると自動でキャンセル扱いになるのでインデックスによる処理でよい
        """
        self.isRenaming = False
        self.parent.SetShortcutEnabled(True)
        if evt.IsEditCancelled():  # ユーザによる編集キャンセル
            return
        e = self.hListCtrl.GetEditControl()
        f = self.listObject.GetElement(self.GetFocusedItem())
        if isinstance(f, browsableObjects.Folder):
            newName = os.path.join(f.directory, e.GetLineText(0))
            error = fileSystemManager.ValidationObjectName(
                newName, fileSystemManager.pathTypes.DIRECTORY, e.GetLineText(0))
        elif isinstance(f, browsableObjects.File):
            newName = os.path.join(f.directory, e.GetLineText(0))
            error = fileSystemManager.ValidationObjectName(
                newName, fileSystemManager.pathTypes.FILE, e.GetLineText(0))
        # end フォルダかファイルか
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
    # end onLabelEditEnd

    def ChangeAttribute(self, attrib_checks):
        lst = self.GetSelectedItems()
        inst = {"operation": "changeAttribute"}
        f = []
        t = []
        for elem in lst:
            attrib = elem.GetNewAttributes(attrib_checks)
            if attrib != -1:  # 変更の必要があるので追加
                f.append(elem.fullpath)
                t.append(attrib)
            # end 追加
        # end 選択中のファイルの数だけ
        inst['from'] = f
        inst['to_attrib'] = t  # to じゃないのは、日時変更に対応していたときのなごり
        op = fileOperator.FileOperator(inst)
        if len(t) == 0:
            dialog(_("情報"), _("変更が必要な俗世はありませんでした。"))
            return
        # end なにも変更しなくてよかった
        ret = op.Execute()
        if op.CheckSucceeded() == 0:
            dialog(_("エラー"), _("属性が変更できません。"))

    def MakeDirectory(self, newdir):
        dir = self.listObject.rootDirectory
        error = fileSystemManager.ValidationObjectName(os.path.join(
            dir, newdir), fileSystemManager.pathTypes.DIRECTORY, newdir)
        if error != "":
            dialog(_("エラー"), error)
            return False
        dest = os.path.join(dir, newdir)
        inst = {"operation": "mkdir", "target": [dest]}
        op = fileOperator.FileOperator(inst)
        ret = op.Execute()
        if op.CheckSucceeded() == 0:
            dialog(_("エラー"), _("フォルダを作成できません。"))
            return
        # end error
        self.UpdateFilelist(silence=True, cursorTargetName=newdir)

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
        if op.CheckSucceeded() == 0:
            dialog(_("エラー"), _("ファイルをゴミ箱に移動できませんでした。"))
            return
        # end error
        failed = op.CheckFailed()
        self.UpdateFilelist(silence=True)
        focus_index = self._findFocusAfterDeletion(paths, focus_index)
        self.Focus(focus_index)

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
        globalVars.app.say(_("コピー"))
        c = clipboard.ClipboardFile()
        c.SetFileList(self.GetSelectedItems().GetItemPaths())
        c.SendToClipboard()

    def Cut(self):
        globalVars.app.say(_("切り取り"))
        c = clipboard.ClipboardFile()
        c.SetOperation(clipboard.MOVE)
        c.SetFileList(self.GetSelectedItems().GetItemPaths())
        c.SendToClipboard()

    def GoToTopFile(self):
        target = self.listObject.GetTopFileIndex()
        if target >= 0:
            self.Focus(target)
            globalVars.app.say(_("先頭ファイル"))
        else:
            self.Focus(self.hListCtrl.GetItemCount() - 1)
            globalVars.app.say(_("ファイルなし"))

    def DirCalc(self):
        lst = []
        for i in self.GetSelectedItems(index_mode=True):
            elem = self.listObject.GetElement(i)
            elem.size = constants.DIR_SIZE_CALCURATING
            self.hListCtrl.RefreshItem(i)
            lst.append((i, elem.fullpath))
        # end for
        param = {'lst': lst, 'callback': self._dirCalc_receive}
        self.background_tasks.append(
            workerThreads.RegisterTask(
                workerThreadTasks.DirCalc, param))

    def _dirCalc_receive(self, results, taskState):
        """DirCalc の結果を受ける。"""
        for elem in results:
            self.listObject.GetElement(elem[0]).size = elem[1][0]
            if elem[1][0] >= 0:
                self.listObject.GetElement(elem[0]).fileCount = elem[1][1]
                self.listObject.GetElement(elem[0]).dirCount = elem[1][2]
            self.hListCtrl.RefreshItem(elem[0])
        # end for
        self.background_tasks.remove(taskState)

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
        folders, files = self.listObject.GetFolderFileNumber()
        if short:
            globalVars.app.say(
                _("フォルダ数 %(folders)d ファイル数 %(files)d") % {
                    'folders': folders,
                    'files': files})
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
            _("%(containing)sの中には、フォルダ %(folders)d個、 ファイル %(files)d個") % {
                'containing': curdir,
                'folders': folders,
                'files': files},
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
        prefix = _("フォルダ ") if len(tmp) > 1 else ""
        globalVars.app.say(
            _("%(prefix)s%(dir)sを %(sortkind)sの%(sortad)sで一覧中、 %(max)d個中 %(current)d個目") % {
                'prefix': prefix,
                'dir': curdir,
                'sortkind': self.listObject.GetSortKindString(),
                'sortad': self.listObject.GetSortAdString(),
                'max': len(
                    self.listObject),
                'current': self.GetFocusedItem() + 1},
            interrupt=True)

    def Past(self):
        dest = self.listObject.rootDirectory
        # クリップボードから情報取得し
        c = clipboard.ClipboardFile()
        # コピー元、コピー先をそれぞれ設定
        target = list(map(lambda x: (x, x.replace(os.path.dirname(x), dest)), c.GetFileList()))
        if not target:
            dialog(_("エラー"), _("貼り付けるものがありません。"))
            return
        # end 貼り付ける物がない
        op = c.GetOperation()
        self.PastOperation(target, self.listObject.rootDirectory, op)

    def PastOperation(self, target, dest, op=clipboard.COPY):
        op_str = _("複写") if op == clipboard.COPY else _("移動")

        # 重複を排除
        # target=set(target)

        # 自身のサブフォルダへの貼り付けはできない
        errors = []
        for it in target:
            i = it[0]
            if i in dest or os.path.dirname(i) == dest:
                errors.append(i)
            # end サブディレクトリ、あるいは、同じディレクトリへのコピー/貼り付け
        # end 事前チェック
        if errors:
            all = ""
            for i in errors:
                target.remove((i, i))
                if all == "SKIP":
                    continue
                # end 「以降も同様に処理」で全てスキップ
                info = [
                    (_("項目"), _("パス")),
                    (_("%s先") % op_str, dest),
                    (os.path.basename(i), i)
                ]
                d = views.OperationSelecter.Dialog(
                    _("自身のサブディレクトリへの%sはできません。") %
                    op_str, info, views.OperationSelecter.GetMethod("OWN_SUB_DIR"), False)
                d.Initialize()
                d.Show()
                ret = d.GetValue()
                if ret["all"]:
                    all = ret["response"]
                # end 「以降も同様に処理」が指定されていたら、そのレスポンスを覚える
                if ret["response"] == "SKIP":
                    continue
                elif ret["response"] == "RENAME":
                    nn = self.getNewNameForPast(os.path.dirname(i), os.path.basename(i))
                    if nn == "":
                        continue
                    # end 名前が入力されなかったらスキップ扱い
                    target.append((i, os.path.join(dest,nn)))
                # end rename
            # エラーの問い合わせ
        # end エラーがある場合

        # この時点でtargetが0ならおわり
        if len(target) == 0:
            return

        # ユーザに確認表示
        if len(target) == 1:
            msg = _("%(file)s\nこのファイルを、 %(dest)s に%(op)sしますか？") % {
                'file': target[0], 'dest': dest, 'op': op_str}
        else:
            msg = _("%(num)d 項目を、 %(dest)s に%(op)sしますか？") % {'num': len(
                target), 'dest': self.listObject.rootDirectory, 'op': op_str}
        # end メッセージどっちにするか
        dlg = wx.MessageDialog(None, msg, _("%(op)sの確認") %
                               {'op': op_str}, wx.YES_NO | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_NO:
            return

        # fileOperatorに処理依頼
        inst = {
            "operation": "past",
            "target": target,
            "to": dest,
            "copy_move_flag": op}
        op = fileOperator.FileOperator(inst)
        ret = op.Execute()

        # 今はテストで、常にダイアログを表示して処理刷る
        nav = {"action": "past", "operator": op}
        globalVars.app.hMainView.Navigate(nav, as_new_tab=True)
        return  # このあとのことは新しいタブに任せる

        # ここから先は今はリーチしない
        # 0.5秒待つ
        time.sleep(0.5)

        # 状況確認
        # TODO:タブに分ける処理
        self.log.debug("Start checking confirmation")
        confs = op.GetConfirmationManager()
        while(True):
            confs_list = list(confs.IterateNotResponded())
            self.log.debug("%d confirmations." % len(confs_list))
            if len(confs_list) == 0:
                break
            elem = confs_list[0]
            e = elem.GetElement()
            from_path = e.path
            dest_path = e.destpath
            from_stat = os.stat(from_path)
            dest_stat = os.stat(dest_path)
            info = [
                (_("名前"), "test.txt", "", ""), (_("サイズ"), misc.ConvertBytesTo(
                    dest_stat.st_size, misc.UNIT_AUTO, True), "→", misc.ConvertBytesTo(
                    from_stat.st_size, misc.UNIT_AUTO, True)), (_("更新日時"), datetime.datetime.fromtimestamp(
                        dest_stat.st_mtime), "→", datetime.datetime.fromtimestamp(
                        from_stat.st_mtime))]
            d = views.OperationSelecter.Dialog(
                _("上書きしますか？"),
                info,
                views.OperationSelecter.GetMethod("ALREADY_EXISTS"),
                False)
            d.Initialize()
            d.Show()
            val = d.GetValue()
            if val['all'] is True:  # 「以降も同様に処理」がオン
                confs.RespondAll(elem, val['response'])
            else:  # この1件だけ
                elem.SetResponse(d.GetValue())  # 渓谷に対して、文字列でレスポンスする
            # end これ以降全てかこれだけか
        # end while
        self.log.debug("End checking confirmation.")
        op.UpdateConfirmation()  # これで繁栄する
        op.Execute()  # これでコピーを再実行

        if op.CheckSucceeded() == 0 and ret == 0:
            dialog(_("エラー"), _("%(op)sに失敗しました。" % {'op': op_str}))
        # end failure
        self.UpdateFilelist(silence=True)
    # end past

    def getNewNameForPast(self, existingDirname, existingName):
        tp = fileSystemManager.pathTypes.DIRECTORY if os.path.isdir(os.path.join(existingDirname,existingName)) else fileSystemManager.pathTypes.FILE
        ret = ""
        input = existingName
        while(True):
            dlg = views.newNameForPast.Dialog()
            dlg.Initialize(input)
            r = dlg.Show()
            if r == wx.ID_CANCEL:
                break
            # end キャンセル
            input = dlg.GetData()
            if input == existingName:
                dialog(_("エラー"), _("新しい名前を入力してください。"))
                continue
            # end 同じファイル名
            error = fileSystemManager.ValidationObjectName(os.path.join(existingDirname, input), tp, input)
            if error:
                dialog(_("エラー"), error)
                continue
            # end バリデーションエラー
            ret = input
            break
        # end 有効なファイル名になるまで
        return ret

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

    def onReactivate(self):
        self.UpdateFilelist(silence=True)
