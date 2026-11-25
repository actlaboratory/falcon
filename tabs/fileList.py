# -*- coding: utf-8 -*-
# Falcon main list tab
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
ファイルリストやドライブ一覧リストなどです。一通りのファイル操作を行うことができます。
"""

import os
import wx

import browsableObjects
import bulk_rename
import clipboard
import constants
import errorCodes
import fileOperator
import fileSystemManager
import globalVars
import lists
import misc
import new_file
import new_shortcut
import operation_manager
import paste_shortcut
import shell_new
import StringUtil
import tabs.streamList
import views.OperationSelecter
import views.newNameForPast
import workerThreads
import workerThreadTasks


from simpleDialog import *
from . import base, navigator

# 名前の一括置換で、変更できなかった項目を表示する最大行数
_MAX_FAILED_LINES = 10


class FileListTab(base.FalconTabBase):
    """ファイル/フォルダリストが表示されているタブ。"""

    def UpdateListContent(self, content, soft=False):
        """
        リストコントロールの中身を更新する。項目数が多くても時間がかからないように、まとめて追加する。
        soft=True の場合は、同一リストの再描画。
        """
        self.log.debug("Updating list control...")
        if soft:
            self.ClearAllItems()
        else:
            self.DeleteAllItems()
        t = misc.Timer()
        for elem in content:
            if elem.hIcon >= 0:
                icon_index = self.GetIconIndex(elem.hIcon)
                if icon_index >= 0:
                    elem.list_imageIndex = icon_index
        self.hListCtrl.set_items(content)
        self.log.debug("List control updated in %f seconds." % t.elapsed)

    def OnLabelEditStart(self, evt):
        """
        ファイル名変更の入力開始イベント
        拡張子を非表示にしていても、拡張子が失われないように、拡張子を含む名前を編集させる
        """
        super().OnLabelEditStart(evt)
        elem = self.listObject.GetElement(evt.GetIndex())
        edit = self.hListCtrl.GetEditControl()
        if edit is not None and elem is not None and edit.GetValue() != elem.basename:
            edit.SetValue(elem.basename)

    def OnLabelEditEnd(self, evt):
        """
                ファイル名変更の入力終了イベント
                入力中にリストが並び替えされると自動でキャンセル扱いになるのでインデックスによる処理でよい
        """
        self.isRenaming = False
        self.parent.set_shortcut_enabled(True)
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

    def GetBulkRenameTargets(self):
        """名前の一括置換の対象(選択中のファイル・フォルダ)を bulk_rename.RenameTarget のリストで返す"""
        targets = []
        for elem in self.GetSelectedItems():
            if isinstance(elem, browsableObjects.File):  # Folder も File の派生
                targets.append(bulk_rename.RenameTarget(elem.fullpath, isinstance(elem, browsableObjects.Folder)))
        return targets

    def BulkRename(self, plans):
        """
        名前の一括置換を実行し、結果を知らせる。
        plans は名前を変更する項目の bulk_rename.RenamePlan のリスト。
        """
        focused = self.GetFocusedElement()
        focused_new_name = ""
        inst = {"operation": "rename", "files": [], "to": []}
        for plan in plans:
            inst["files"].append(plan.target.fullpath)
            inst["to"].append(plan.new_fullpath)
            if focused is not None and plan.target.fullpath == focused.fullpath:
                focused_new_name = plan.new_name
        op = fileOperator.FileOperator(inst)
        op.Execute()
        succeeded = op.CheckSucceeded()
        # 開発時は権限の昇格ができず、失敗した項目が記録されないことがあるため、件数は成功数から求める
        failed_count = len(plans) - succeeded
        self.UpdateFilelist(silence=True, cursorTargetName=focused_new_name)
        if failed_count <= 0:
            globalVars.app.say(_("%(count)d件の名前を変更しました。") % {"count": succeeded}, interrupt=True)
            return
        failed_paths = [e.elem for e in op.CheckFailed()]
        lines = failed_paths[:_MAX_FAILED_LINES]
        if len(failed_paths) > _MAX_FAILED_LINES:
            lines.append(_("ほか %(count)d件") % {"count": len(failed_paths) - _MAX_FAILED_LINES})
        dialog(_("エラー"), _("%(succeeded)d件の名前を変更しました。\n%(failed)d件は名前を変更できませんでした。\n\n%(lines)s") % {
            "succeeded": succeeded, "failed": failed_count, "lines": "\n".join(lines)})

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

    def MakeFile(self, request):
        """
        今のディレクトリに新しいファイルを作り、作ったファイルにカーソルを合わせる。
        request は new_file.NewFileRequest。
        """
        directory = self.listObject.rootDirectory
        error = new_file.validate(directory, request.name)
        if error == "":
            error = new_file.create(os.path.join(directory, request.name), request.file_type)
        if error != "":
            errorDialog(error)
            return False
        if request.file_type.method == shell_new.METHOD_COMMAND:
            # ファイルは起動したプログラムが作るので、まだ無いことがある
            self.UpdateFilelist(silence=True)
            return True
        self.UpdateFilelist(silence=True, cursorTargetName=request.name)
        return True

    def MakeNewShortcut(self, request):
        """
        今のディレクトリに新しいショートカットを作り、作ったショートカットにカーソルを合わせる。
        request は new_shortcut.NewShortcutRequest。
        """
        error = new_shortcut.create(self.listObject.rootDirectory, request)
        if error != "":
            errorDialog(error)
            return False
        self.UpdateFilelist(silence=True, cursorTargetName=request.name)
        return True

    def FileOperationTest(self):
        if self.task:
            self.task.Cancel()
        else:
            self.task = workerThreads.RegisterTask(workerThreadTasks.DebugBeep)

    def Trash(self):
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
        globalVars.app.main_window.operations.add(operation_manager.DeleteOperation(
            fileOperator.FileOperator({"operation": "trash", "target": target})))

    def Delete(self):
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
        globalVars.app.main_window.operations.add(operation_manager.DeleteOperation(
            fileOperator.FileOperator({"operation": "delete", "target": target})))

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
        try:
            paths = c.GetFileList()
        except Exception:
            self.log.exception("cannot get file list from clipboard")
            paths = []
        if not paths:
            dialog(_("エラー"), _("貼り付けるものがありません。"))
            return
        # end 貼り付ける物がない
        try:
            # エクスプローラーのコピーは「コピーまたはリンク」(5)になるので、移動だけが指定されているとき以外はコピーにする
            op = clipboard.MOVE if c.GetOperation() == clipboard.MOVE else clipboard.COPY
        except Exception:
            # Preferred DropEffect を付けないアプリからのコピーはコピー扱いにする
            op = clipboard.COPY
        self.PastOperation(paths, dest, op)

    def PasteShortcut(self):
        """クリップボードの項目のショートカットを今のディレクトリに作る（エクスプローラーの「ショートカットの貼り付け」）。"""
        c = clipboard.ClipboardFile()
        try:
            targets = c.GetFileList()
        except Exception:
            self.log.exception("cannot get file list from clipboard")
            targets = []
        if not targets:
            dialog(_("エラー"), _("貼り付けるものがありません。"))
            return False
        try:
            op = c.GetOperation()
        except Exception:
            # Preferred DropEffect を付けないアプリからのコピーはコピー扱いにする
            op = clipboard.COPY
        # エクスプローラーでは、切り取った項目はショートカットとして貼り付けられない
        if op == clipboard.MOVE:
            dialog(_("エラー"), _("切り取った項目は、ショートカットとして貼り付けられません。コピーしてから貼り付けてください。"))
            return False
        result = paste_shortcut.paste(targets, self.listObject.rootDirectory)
        cursor_target = result.created[0] if result.created else ""
        self.UpdateFilelist(silence=True, cursorTargetName=cursor_target)
        if not result.failed:
            globalVars.app.say(_("%(count)d件のショートカットを作成しました。") % {"count": len(result.created)}, interrupt=True)
            return True
        lines = ["%s: %s" % (path, error.replace("\n", " ")) for path, error in result.failed[:_MAX_FAILED_LINES]]
        if len(result.failed) > _MAX_FAILED_LINES:
            lines.append(_("ほか %(count)d件") % {"count": len(result.failed) - _MAX_FAILED_LINES})
        dialog(_("エラー"), _("%(succeeded)d件のショートカットを作成しました。\n%(failed)d件はショートカットを作成できませんでした。\n\n%(lines)s") % {
            "succeeded": len(result.created), "failed": len(result.failed), "lines": "\n".join(lines)})
        return False

    def PastOperation(self, target, dest, op=clipboard.COPY):
        op_str = _("複写") if op == clipboard.COPY else _("移動")

        # コピー元、コピー先をそれぞれ設定。ドラッグアンドドロップの場合も、パスのリストで渡される
        target = [(path, os.path.join(dest, os.path.basename(path))) for path in target]

        # 自身のサブフォルダへの貼り付けはできない
        errors = []
        # リンクを経由した場所でも判定できるよう、実際のパスで比べる。項目自体がリンクの場合は、リンクのある場所で比べる
        destination = os.path.normcase(os.path.realpath(dest))
        real_parents = {}
        for it in target:
            i = it[0]
            parent = os.path.dirname(i)
            if parent not in real_parents:
                real_parents[parent] = os.path.realpath(parent)
            source = os.path.normcase(os.path.join(real_parents[parent], os.path.basename(i)))
            if destination == source or destination.startswith(os.path.join(source, "")) or os.path.dirname(source) == destination:
                errors.append(i)
            # end サブディレクトリ、あるいは、同じディレクトリへのコピー/貼り付け
        # end 事前チェック
        if errors:
            all = ""
            for i in errors:
                target.remove((i, os.path.join(dest, os.path.basename(i))))
                if all == "SKIP":
                    continue
                # end 「以降も同様に処理」で全てスキップ
                if all == "RENAME":
                    nn = self.getNewNameForPast(os.path.dirname(i), os.path.basename(i))
                    if nn == "":
                        continue
                    # end 名前が入力されなかったらスキップ扱い
                    target.append((i, os.path.join(dest, nn)))
                    continue
                # 「以降も同様に処理」ででリネーム
                info = [
                    (_("項目"), _("パス")),
                    (_("%s先") % op_str, dest),
                    (os.path.basename(i), i)
                ]
                ret = globalVars.app.main_window.showSubWindow(
                    views.OperationSelecter.OperationSelecterWindow, _("ファイル操作確認"),
                    views.OperationSelecter.OperationSelecterParameters(_("自身のサブディレクトリへの%sはできません。") % op_str, info, views.OperationSelecter.GetMethod("OWN_SUB_DIR"), False)).user_object
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
                    target.append((i, os.path.join(dest, nn)))
                # end rename
            # エラーの問い合わせ
        # end エラーがある場合

        # この時点でtargetが0ならおわり
        if len(target) == 0:
            return

        # ユーザに確認表示
        if len(target) == 1:
            msg = _("%(file)s\nこのファイルを、 %(dest)s に%(op)sしますか？") % {
                'file': target[0][0], 'dest': target[0][1], 'op': op_str}
        else:
            msg = _("%(num)d 項目を、 %(dest)s に%(op)sしますか？") % {'num': len(
                target), 'dest': dest, 'op': op_str}
        # end メッセージどっちにするか
        dlg = wx.MessageDialog(None, msg, _("%(op)sの確認") %
                               {'op': op_str}, wx.YES_NO | wx.ICON_QUESTION)
        answer = dlg.ShowModal()
        dlg.Destroy()
        if answer == wx.ID_NO:
            return

        # fileOperatorに処理依頼
        inst = {
            "operation": "past",
            "target": target,
            "to": dest,
            "copy_move_flag": op}
        # 別スレッドで実行し、一覧の更新や結果の通知もそちらに任せる
        globalVars.app.main_window.operations.add(operation_manager.PasteOperation(fileOperator.FileOperator(inst)))
    # end past

    def getNewNameForPast(self, existingDirname, existingName):
        tp = fileSystemManager.pathTypes.DIRECTORY if os.path.isdir(os.path.join(existingDirname, existingName)) else fileSystemManager.pathTypes.FILE
        ret = ""
        input = existingName
        while(True):
            result = globalVars.app.main_window.showSubWindow(views.newNameForPast.NewNameForPastWindow, _("新しい名前を入力"), input)
            if result.code == wx.ID_CANCEL:
                break
            # end キャンセル
            input = result.user_object
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

    def GoBackward(self):
        """内包しているフォルダ/ドライブ一覧へ移動する。"""
        return navigator.go_to_parent(self, self.listObject.rootDirectory)

    def GetTabName(self):
        """タブコントロールに表示する名前"""
        word = os.path.basename(self.listObject.rootDirectory)
        if word == "":  # ルート
            word = self.listObject.rootDirectory
        word = StringUtil.GetLimitedString(
            word, globalVars.app.settings.get_int("view", "header_title_length", 20, 1))
        return word

    def GetRootObject(self):
        """ドライブ詳細情報表示で用いる"""
        return misc.GetRootObject(self.listObject.rootDirectory)

    def onReactivate(self):
        pass
