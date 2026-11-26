# -*- coding: utf-8 -*-
# Falcon remote list tab
# Note: All comments except these top lines will be written in Japanese.

"""
FTP・SFTP のサーバー上のフォルダを表示するタブです。
閲覧とダウンロードだけができます。ファイルの変更・削除・アップロードはできません。
"""

import os
import tempfile
import uuid

import wx

import background_wait
import browsableObjects
import errorCodes
import globalVars
import misc
import network_place
import remote_connect
import remote_storage

from simpleDialog import dialog
from . import base

# 開くためにダウンロードしたファイルを置くフォルダ
_TEMP_DIRECTORY_NAME = "falcon_remote"


class RemoteListTab(base.FalconTabBase):
    """FTP・SFTP のサーバー上のフォルダを表示するタブ。"""

    def GoForward(self, stream, admin=False):
        """フォルダなら中に入り、ファイルならダウンロードして開く"""
        elem = self.GetFocusedElement()
        if isinstance(elem, browsableObjects.RemoteFolder):
            return self.Move(elem.fullpath)
        if isinstance(elem, browsableObjects.RemoteFile):
            return self._open_file(elem)
        return errorCodes.NOT_SUPPORTED

    def _open_file(self, elem):
        """ファイルを一時フォルダにダウンロードして、関連付けられたアプリで開く"""
        directory = os.path.join(tempfile.gettempdir(), _TEMP_DIRECTORY_NAME, uuid.uuid4().hex)
        try:
            os.makedirs(directory)
        except OSError as err:
            dialog(_("エラー"), _("一時フォルダを作れませんでした。\n(%(error)s)") % {"error": err})
            return errorCodes.ACCESS_DENIED
        local_path = os.path.join(directory, elem.basename)
        globalVars.app.say(_("ダウンロード中"), interrupt=True)
        try:
            remote_connect.run(elem.location, _download, elem.path, local_path, pass_task=True)
        except background_wait.Canceled:
            return errorCodes.CANCELED
        except (remote_storage.RemoteError, OSError) as err:
            self.log.error("Cannot download %s: %s" % (elem.fullpath, err))
            dialog(_("エラー"), _("%(name)s をダウンロードできませんでした。\n%(error)s") % {"name": elem.basename, "error": err})
            return errorCodes.ACCESS_DENIED
        misc.RunFile(local_path, admin=False, workdir=directory)
        return errorCodes.OK

    def GoBackward(self):
        """親フォルダへ移動する。ルートではドライブ一覧へ移動する"""
        location = self.listObject.location
        parent = remote_storage.get_parent_path(location.path)
        if parent is None:
            return self.Move("", network_place.find_name(self.listObject.rootDirectory))
        return self.Move(location.get_url(parent), location.path.rsplit("/", 1)[-1])

    def OnLabelEditEnd(self, evt):
        # 名前の変更はできない
        self.isRenaming = False
        self.parent.set_shortcut_enabled(True)
        evt.Veto()

    def BeginDrag(self, event):
        # サーバー上の項目は、エクスプローラーなどにドラッグできない
        pass

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
        commands = ["MOVE_FORWARD", "TOOL_DOWNLOAD", "EDIT_FULLPATHCOPY", "EDIT_UPDATEFILELIST", "TOOL_ADD_NETWORK_PLACE"]
        if self.GetFocusedElement() is None:
            commands = commands[3:]
        globalVars.app.main_window.menu.register_menu_command(menu, commands)
        globalVars.app.main_window.PopupMenu(menu)


def _download(client, task, path, local_path):
    """(別スレッド)ファイルをダウンロードする。中止されたら途中までのファイルを消す"""
    client.download(path, local_path, lambda size: task.check_canceled())
