# -*- coding: utf-8 -*-
# Falcon compress view
# Note: All comments except these top lines will be written in Japanese.

"""圧縮の形式や保存先を入力するウィンドウ"""

import os

import viewkit
import wx

import archiver
import fileSystemManager
import simpleDialog


class CompressParameters:
    """CompressWindow に渡すパラメータ"""

    def __init__(self, sources: list, directory: str):
        # 圧縮するファイル・フォルダのフルパス
        self.sources = sources
        # 保存先の初期値
        self.directory = directory


class CompressWindow(viewkit.SubWindow):
    """圧縮の形式や保存先を入力するウィンドウ。結果は archiver.CompressRequest。"""

    def __init__(self, parent, ctx, title, parameters: CompressParameters):
        super().__init__(parent, ctx, title, parameters)
        self._request = None
        self._formats = archiver.get_compress_formats()

        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        self.format, dummy = creator.combobox(
            _("形式"), [f.name for f in self._formats], self._on_format_changed, state=0)
        self.name, dummy = creator.inputbox(
            _("書庫の名前（拡張子は自動で付きます）"), default_value=self._get_default_name(), x=400,
            style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
        self.name.hideScrollBar(wx.HORIZONTAL)
        directory_creator = creator.makeChild(wx.HORIZONTAL, 0, "", wx.ALL | wx.EXPAND, margin=0)
        self.directory, dummy = directory_creator.inputbox(
            _("保存先のフォルダ"), default_value=parameters.directory, x=400, style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
        self.directory.hideScrollBar(wx.HORIZONTAL)
        directory_creator.button(_("参照"), self._on_browse)
        self.password, dummy = creator.inputbox(
            _("パスワード（空欄なら付けません）"), x=400, style=wx.BORDER_RAISED | wx.TE_PASSWORD)
        self.confirmation, dummy = creator.inputbox(
            _("パスワードの確認"), x=400, style=wx.BORDER_RAISED | wx.TE_PASSWORD)
        self._update_password()

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

    def _get_default_name(self):
        """書庫の名前の初期値。1件ならその名前、複数なら今のフォルダの名前にする。"""
        path = self.parameters.sources[0]
        stem = os.path.basename(path)
        if not os.path.isdir(path):
            stem = os.path.splitext(stem)[0]
        if len(self.parameters.sources) > 1:
            stem = os.path.basename(self.parameters.directory.rstrip("\\")) or stem
        return archiver.make_unique_name(self.parameters.directory, stem, self._formats[0].extension)

    def _get_format(self):
        return self._formats[max(0, self.format.GetSelection())]

    def _on_format_changed(self, event):
        self._update_password()
        event.Skip()

    def _update_password(self):
        """パスワードを付けられない形式では、入力欄を無効にする"""
        enable = self._get_format().supports_password
        self.password.Enable(enable)
        self.confirmation.Enable(enable)

    def _on_browse(self, event):
        d = wx.DirDialog(self, _("保存先のフォルダを選択"), defaultPath=self.directory.GetLineText(0))
        if d.ShowModal() != wx.ID_CANCEL:
            self.directory.SetValue(d.GetPath())
        d.Destroy()
        self.directory.SetFocus()

    def _on_ok(self, event):
        error, field = self._make_request()
        if error:
            simpleDialog.errorDialog(error, self)
            field.SetFocus()
            return
        event.Skip()

    def _make_request(self):
        """入力内容を検証して結果を作る。問題があれば、エラーメッセージと修正が必要な入力欄を返す。"""
        archive_format = self._get_format()
        directory = os.path.expandvars(self.directory.GetLineText(0).strip().strip("\""))
        if not os.path.isabs(directory) or not os.path.isdir(directory):
            return _("保存先のフォルダが見つかりません。"), self.directory
        name = self.name.GetLineText(0).strip()
        if name == "":
            return _("書庫の名前を入力してください。"), self.name
        if not name.lower().endswith(archive_format.extension):
            name += archive_format.extension
        destination = os.path.join(os.path.abspath(directory), name)
        error = fileSystemManager.ValidationObjectName(destination, fileSystemManager.pathTypes.FILE, name)
        if error:
            return error, self.name
        if os.path.lexists(destination):
            return _("同じ名前のファイルまたはフォルダがすでにあります。"), self.name
        password = self.password.GetValue() if archive_format.supports_password else ""
        if password != (self.confirmation.GetValue() if archive_format.supports_password else ""):
            return _("パスワードと、確認のパスワードが一致しません。"), self.password
        if "\"" in password:
            return _("パスワードに「\"」は使えません。"), self.password
        if archive_format.extension == ".zip" and not password.isascii():
            # 文字コードの決まりがなく、ほかのソフトで解凍できないことがある
            return _("ZIP のパスワードには、半角の英数字と記号だけを使ってください。"), self.password
        self._request = archiver.CompressRequest(self.parameters.sources, destination, archive_format, password)
        return "", None

    def result(self):
        return self._request
