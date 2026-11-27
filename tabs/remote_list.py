# -*- coding: utf-8 -*-
# Falcon remote list tab
# Note: All comments except these top lines will be written in Japanese.

"""
FTP・SFTP のサーバー上のフォルダを表示するタブです。
閲覧のほか、ダウンロード・アップロード（貼り付け、ドラッグアンドドロップ）、フォルダ・ファイルの作成、
名前の変更、同じサーバーの中での移動（切り取りと貼り付け）、削除、パーミッションの変更ができます。
"""

import os
import uuid

import wx

import background_wait
import browsableObjects
import clipboard
import errorCodes
import globalVars
import misc
import network_place
import operation_manager
import remote_clipboard
import remote_connect
import remote_edit
import remote_storage
import remote_transfer
import views.transfer_conflict

from simpleDialog import dialog
from . import base

# エラーの一覧で表示する件数
_MAX_ERROR_LINES = 10


class RemoteListTab(base.FalconTabBase):
    """FTP・SFTP のサーバー上のフォルダを表示するタブ。"""

    def GoForward(self, stream, admin=False):
        """フォルダなら中に入り、ファイルならダウンロードして開く。stream=True（右矢印キー）ではフォルダに入るだけ"""
        elem = self.GetFocusedElement()
        if isinstance(elem, browsableObjects.RemoteFolder):
            return self.Move(elem.fullpath)
        if isinstance(elem, browsableObjects.RemoteFile) and not stream:
            return self._open_file(elem)
        return errorCodes.NOT_SUPPORTED

    def _open_file(self, elem):
        """
        ファイルを一時フォルダにダウンロードして、関連付けられたアプリで開く。
        開いたファイルを編集して保存した場合は、falcon に戻ったときにアップロードするかを尋ねる（remote_edit）。
        """
        directory = os.path.join(remote_edit.get_temp_root(), uuid.uuid4().hex)
        try:
            os.makedirs(directory)
        except OSError as err:
            dialog(_("エラー"), _("一時フォルダを作成できませんでした。\n(%(error)s)") % {"error": err})
            return errorCodes.ACCESS_DENIED
        local_path = os.path.join(directory, remote_transfer.get_local_name(elem.basename))
        globalVars.app.say(_("ダウンロード中"), interrupt=True)
        try:
            remote_connect.run(elem.location, _download, elem.path, local_path, pass_task=True)
        except background_wait.Canceled:
            return errorCodes.CANCELED
        except (remote_storage.RemoteError, OSError) as err:
            # 利用者向けの文章（翻訳されている）ではなく、英語の説明をログに書く
            self.log.error("Cannot download %s: %s" % (elem.fullpath, remote_storage.get_log_text(err)))
            dialog(_("エラー"), _("%(name)s をダウンロードできませんでした。\n%(error)s") % {"name": elem.basename, "error": err})
            return errorCodes.ACCESS_DENIED
        # インターネットから来たファイルとして扱わせる（SmartScreen や Office の保護ビューのため）
        remote_transfer.mark_from_internet(local_path, elem.location.get_url(elem.path, with_user=False))
        remote_edit.edit_tracker.add(local_path, elem.location, elem.path)
        misc.RunFile(local_path, admin=False, workdir=directory)
        return errorCodes.OK

    def GoBackward(self):
        """親フォルダへ移動する。ルートではドライブ一覧へ移動する"""
        location = self.listObject.location
        parent = remote_storage.get_parent_path(location.path)
        if parent is None:
            return self.Move("", network_place.find_name(self.listObject.rootDirectory))
        return self.Move(location.get_url(parent), location.path.rsplit("/", 1)[-1])

    # ---- 作成・名前の変更・移動・削除 ----

    def _get_names(self):
        """表示中のフォルダにある項目の名前の集まり"""
        return {elem.basename for elem in self.listObject.GetItemList()}

    def _run(self, func, *args):
        """
        表示中のサーバーで func(client, *args) を実行する。失敗した場合はエラーを表示して None を返す。
        中止された場合も None を返す。成功した場合は func の戻り値（None の場合は True）を返す。
        """
        try:
            result = remote_connect.run(self.listObject.location, func, *args)
        except background_wait.Canceled:
            return None
        except remote_storage.RemoteError as err:
            self.log.error("remote operation failed: %s" % remote_storage.get_log_text(err))
            dialog(_("エラー"), str(err))
            return None
        return True if result is None else result

    def _check_new_name(self, name):
        """新しく作る・付ける名前を調べ、使えなければエラーを表示して False を返す"""
        error = remote_storage.validate_name(name)
        if error == "" and name in self._get_names():
            error = _("同名の項目が既に存在します。")
        if error:
            dialog(_("エラー"), error)
            return False
        return True

    def MakeDirectory(self, name):
        """表示中のフォルダに、新しいフォルダを作る"""
        if not self._check_new_name(name):
            return False
        path = remote_storage.join_path(self.listObject.location.path, name)
        if self._run(lambda client: client.make_dir(path)) is None:
            return False
        self.UpdateFilelist(silence=True, cursorTargetName=name)
        return True

    def make_empty_file(self, name):
        """表示中のフォルダに、空のファイルを作る"""
        if not self._check_new_name(name):
            return False
        path = remote_storage.join_path(self.listObject.location.path, name)
        if self._run(lambda client: client.create_file(path)) is None:
            return False
        self.UpdateFilelist(silence=True, cursorTargetName=name)
        return True

    def OnLabelEditStart(self, evt):
        super().OnLabelEditStart(evt)
        # 入力中に一覧が更新されても対象が変わらないよう、項目で持つ
        self.renaming_element = self.listObject.GetElement(evt.GetIndex())

    def OnLabelEditEnd(self, evt):
        """名前の変更の入力が終わった。サーバー上で名前を変えてから、一覧を更新する"""
        self.isRenaming = False
        self.parent.set_shortcut_enabled(True)
        elem = getattr(self, "renaming_element", None)
        self.renaming_element = None
        if evt.IsEditCancelled() or elem is None:
            return
        name = self.hListCtrl.GetEditControl().GetLineText(0)
        # 一覧の表示は、サーバーで変更できてから更新する
        evt.Veto()
        if name == elem.basename:
            return
        if not self._check_new_name(name):
            return
        # 入力欄を閉じてから、サーバーとやり取りする
        wx.CallAfter(self._rename, elem, name)

    def _rename(self, elem, name):
        new_path = remote_storage.join_path(remote_storage.get_parent_path(elem.path), name)
        if self._run(lambda client: client.rename(elem.path, new_path)) is None:
            return
        self.UpdateFilelist(silence=True, cursorTargetName=name)

    def Trash(self):
        """サーバーにはごみ箱がないので、確認してから完全に削除する"""
        self.Delete()

    def Delete(self):
        """選択中の項目を、確認してからサーバーから削除する"""
        elems = [elem for elem in self.GetSelectedItems() if isinstance(elem, browsableObjects.RemoteFile)]
        if not elems:
            return
        if len(elems) == 1:
            message = _("%(name)s\nサーバーから完全に削除しますか？\nこの操作は元に戻せません。") % {"name": elems[0].basename}
        else:
            message = _("選択した %(count)d件をサーバーから完全に削除しますか？\nこの操作は元に戻せません。") % {"count": len(elems)}
        dlg = wx.MessageDialog(None, message, _("削除の確認"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
        answer = dlg.ShowModal()
        dlg.Destroy()
        if answer != wx.ID_YES:
            return
        items = [remote_transfer.DownloadItem(elem.path, isinstance(elem, browsableObjects.RemoteFolder), elem.is_link) for elem in elems]
        request = remote_transfer.DeleteRequest(self.listObject.location, items)
        globalVars.app.main_window.operations.add(operation_manager.RemoteDeleteOperation(request))

    def change_permissions(self, elems, mode):
        """項目のパーミッションを変える"""
        def change(client):
            errors = []
            for elem in elems:
                try:
                    client.chmod(elem.path, mode)
                except remote_storage.ConnectError:
                    raise
                except remote_storage.RemoteError as err:
                    errors.append((elem.basename, str(err)))
            return errors

        errors = self._run(change)
        if errors is None:
            return
        self.UpdateFilelist(silence=True)
        if errors is not True and errors:
            _show_errors(_("一部の項目のパーミッションを変更できませんでした。"), errors)
            return
        globalVars.app.say(_("パーミッションを変更しました。"), interrupt=True)

    # ---- コピー・切り取り・貼り付け ----

    def _get_selected_transfer_items(self):
        return [
            remote_transfer.DownloadItem(elem.path, isinstance(elem, browsableObjects.RemoteFolder), elem.is_link)
            for elem in self.GetSelectedItems() if isinstance(elem, browsableObjects.RemoteFile)]

    def Copy(self):
        """選択中の項目を覚える。ファイル一覧で貼り付けるとダウンロードする"""
        items = self._get_selected_transfer_items()
        if not items:
            return
        globalVars.app.say(_("コピー"))
        remote_clipboard.remote_clipboard.set(self.listObject.location, items, clipboard.COPY)

    def Cut(self):
        """選択中の項目を覚える。同じサーバーの別のフォルダで貼り付けると移動する"""
        items = self._get_selected_transfer_items()
        if not items:
            return
        globalVars.app.say(_("切り取り"))
        remote_clipboard.remote_clipboard.set(self.listObject.location, items, clipboard.MOVE)

    def Past(self):
        """
        貼り付け。サーバー上で切り取った項目なら、表示中のフォルダに移動する。
        ファイル一覧などでコピーしたファイルなら、表示中のフォルダにアップロードする。
        """
        data = remote_clipboard.remote_clipboard.get()
        if data is not None:
            return self._paste_remote(data)
        c = clipboard.ClipboardFile()
        try:
            paths = c.GetFileList()
        except Exception:
            self.log.exception("cannot get file list from clipboard")
            paths = []
        if not paths:
            dialog(_("エラー"), _("貼り付けるものがありません。"))
            return
        try:
            op = clipboard.MOVE if c.GetOperation() == clipboard.MOVE else clipboard.COPY
        except Exception:
            # Preferred DropEffect を付けないアプリからのコピーはコピー扱いにする
            op = clipboard.COPY
        self.PastOperation(paths, self.listObject.rootDirectory, op)

    def _paste_remote(self, data):
        """サーバー上で切り取った項目を、表示中のフォルダに移動する"""
        destination = self.listObject.location
        if not data.is_move():
            dialog(_("エラー"), _(
                "サーバー内でのコピーには対応していません。\n"
                "移動は切り取り、ダウンロードはファイル一覧のタブへの貼り付けで行ってください。"))
            return
        if not remote_storage.is_same_server(data.location, destination):
            dialog(_("エラー"), _("切り取った項目は同じサーバー内でのみ移動できます。"))
            return
        if data.location.path == destination.path:
            dialog(_("エラー"), _("移動元と移動先が同じフォルダです。"))
            return
        for item in data.items:
            if item.is_dir and (destination.path + "/").startswith(item.path.rstrip("/") + "/"):
                dialog(_("エラー"), _("フォルダをそれ自身またはサブフォルダに移動することはできません。"))
                return
        names = self._get_names()
        conflicts = [item.get_name() for item in data.items if item.get_name() in names]
        if conflicts:
            dialog(_("エラー"), _("移動先に同名の項目が存在します。\n%(names)s") % {"names": "\n".join(conflicts[:_MAX_ERROR_LINES])})
            return

        def move(client):
            errors = []
            for item in data.items:
                try:
                    client.rename(item.path, remote_storage.join_path(destination.path, item.get_name()))
                except remote_storage.ConnectError:
                    raise
                except remote_storage.RemoteError as err:
                    errors.append((item.get_name(), str(err)))
            return errors

        errors = self._run(move)
        if errors is None:
            return
        remote_clipboard.remote_clipboard.clear()
        self.UpdateFilelist(silence=True, cursorTargetName=data.items[0].get_name())
        # 移動元のフォルダを表示しているタブも更新する
        globalVars.app.main_window.refresh_file_lists({data.location.get_url()})
        if errors is not True and errors:
            _show_errors(_("一部の項目を移動できませんでした。"), errors)
            return
        globalVars.app.say(_("%(count)d件を移動しました。") % {"count": len(data.items)}, interrupt=True)

    def PastOperation(self, target, dest, op=clipboard.COPY):
        """
        ローカルのファイル・フォルダ（target はパスのリスト）を、dest のフォルダにアップロードする。
        貼り付けとドラッグアンドドロップで使う。dest は表示中のフォルダの URL。
        """
        if op == clipboard.MOVE:
            dialog(_("エラー"), _("ローカルからサーバーへの移動には対応していません。コピーして貼り付けてください。"))
            return
        if not target:
            return
        location = self.listObject.location
        if dest != self.listObject.rootDirectory:
            location = remote_storage.parse_url(dest)
        items = [remote_transfer.UploadItem(path) for path in target]
        conflict = remote_transfer.CONFLICT_RENAME
        if location.path == self.listObject.location.path:
            names = self._get_names()
            conflicts = [item.get_name() for item in items if item.get_name() in names]
            if conflicts:
                result = globalVars.app.main_window.showSubWindow(
                    views.transfer_conflict.TransferConflictWindow, _("アップロード"), conflicts)
                if getattr(result, "code", wx.ID_CANCEL) == wx.ID_CANCEL:
                    return
                conflict = result.user_object
        request = remote_transfer.UploadRequest(location, items, conflict)
        globalVars.app.main_window.operations.add(operation_manager.UploadOperation(request))

    def upload_files(self):
        """ファイルを選んで、表示中のフォルダにアップロードする。フォルダは貼り付けかドラッグアンドドロップで"""
        d = wx.FileDialog(
            globalVars.app.main_window, _("アップロードするファイルの選択"),
            style=wx.FD_OPEN | wx.FD_MULTIPLE | wx.FD_FILE_MUST_EXIST)
        answer = d.ShowModal()
        paths = d.GetPaths()
        d.Destroy()
        if answer == wx.ID_CANCEL or not paths:
            return
        self.PastOperation(paths, self.listObject.rootDirectory)

    def BeginDrag(self, event):
        # サーバー上の項目は、エクスプローラーなどにドラッグできない
        pass

    # ---- 読み上げ ----

    def ReadCurrentFolder(self):
        globalVars.app.say(_("現在は、%(host)sの %(folder)s") % {
            "host": self.listObject.location.get_display_host(), "folder": self._get_folder_name()}, interrupt=True)

    def _get_folder_name(self):
        path = self.listObject.location.path
        return _("ルート") if path == "/" else path.rsplit("/", 1)[-1]

    def ReadListItemNumber(self, short=False):
        folders, files = len(self.listObject.folders), len(self.listObject.files)
        if short:
            globalVars.app.say(_("フォルダ数 %(folders)d ファイル数 %(files)d") % {"folders": folders, "files": files})
            return
        globalVars.app.say(_("%(dir)sには、フォルダ %(folders)d個、 ファイル %(files)d個") % {
            "dir": self._get_folder_name(), "folders": folders, "files": files}, interrupt=True)

    def ReadListInfo(self):
        globalVars.app.say(_("%(host)sの %(dir)sを %(sortkind)sの%(sortad)sで一覧中、 %(max)d個中 %(current)d個目") % {
            "host": self.listObject.location.get_display_host(),
            "dir": self._get_folder_name(),
            "sortkind": self.listObject.GetSortKindString(),
            "sortad": self.listObject.GetSortAdString(),
            "max": len(self.listObject),
            "current": self.GetFocusedItem() + 1}, interrupt=True)

    def GetTabName(self):
        """タブコントロールに表示する名前"""
        location = self.listObject.location
        return location.get_display_host() if location.path == "/" else location.path.rsplit("/", 1)[-1]

    def OpenContextMenu(self, event):
        menu = wx.Menu()
        if self.GetFocusedElement() is None:
            commands = ["EDIT_PAST", "FILE_MKDIR", "TOOL_UPLOAD", "EDIT_UPDATEFILELIST", "TOOL_ADD_NETWORK_PLACE"]
        else:
            commands = [
                "MOVE_FORWARD", "TOOL_DOWNLOAD", "TOOL_UPLOAD", "EDIT_COPY", "EDIT_CUT", "EDIT_PAST",
                "FILE_RENAME", "FILE_DELETE", "FILE_CHANGEATTRIBUTE", "FILE_MKDIR", "EDIT_FULLPATHCOPY",
                "FILE_VIEW_DETAIL", "EDIT_UPDATEFILELIST", "TOOL_ADD_NETWORK_PLACE"]
        globalVars.app.main_window.menu.register_menu_command(menu, commands)
        globalVars.app.main_window.PopupMenu(menu)


def _download(client, task, path, local_path):
    """(別スレッド)ファイルをダウンロードする。中止されたら途中までのファイルを消す"""
    client.download(path, local_path, lambda size: task.check_canceled())


def _show_errors(message, errors):
    """(対象, 内容) のリストをエラーとして表示する"""
    lines = ["%s: %s" % (name, error.replace("\n", " ")) for name, error in errors[:_MAX_ERROR_LINES]]
    if len(errors) > _MAX_ERROR_LINES:
        lines.append(_("ほか %(count)d件") % {"count": len(errors) - _MAX_ERROR_LINES})
    dialog(_("エラー"), "%s\n\n%s" % (message, "\n".join(lines)))
