# -*- coding: utf-8 -*-
# Falcon extract view
# Note: All comments except these top lines will be written in Japanese.

"""解凍の展開先を入力するウィンドウと、書庫のパスワードを入力するウィンドウ"""

import os

import viewkit
import wx

import archiver
import simpleDialog


class ExtractWindow(viewkit.SubWindow):
    """解凍の展開先を入力するウィンドウ。parameters は展開先の初期値。結果は archiver.ExtractRequest。"""

    def __init__(self, parent, ctx, title, parameters: str):
        super().__init__(parent, ctx, title, parameters)
        self._request = None
        self._conflicts = [archiver.CONFLICT_RENAME, archiver.CONFLICT_SKIP, archiver.CONFLICT_OVERWRITE]

        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        directory_creator = creator.makeChild(wx.HORIZONTAL, 0, "", wx.ALL | wx.EXPAND, margin=0)
        self.directory, dummy = directory_creator.inputbox(
            _("展開先のフォルダ"), default_value=parameters, x=400, style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
        self.directory.hideScrollBar(wx.HORIZONTAL)
        directory_creator.button(_("参照"), self._on_browse)
        self.make_folder = creator.checkbox(_("書庫の名前のフォルダを作って展開する"), state=True)
        self.conflict, dummy = creator.combobox(
            _("同じ名前のファイルがあるとき"), [_("別の名前で展開する"), _("展開しない"), _("上書きする")], state=0)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

    def _on_browse(self, event):
        d = wx.DirDialog(self, _("展開先のフォルダを選択"), defaultPath=self.directory.GetLineText(0))
        if d.ShowModal() != wx.ID_CANCEL:
            self.directory.SetValue(d.GetPath())
        d.Destroy()
        self.directory.SetFocus()

    def _on_ok(self, event):
        directory = os.path.expandvars(self.directory.GetLineText(0).strip().strip("\""))
        if not os.path.isabs(directory) or os.path.isfile(directory):
            simpleDialog.errorDialog(_("展開先のフォルダを、ドライブ名から正しく入力してください。"), self)
            self.directory.SetFocus()
            return
        self._request = archiver.ExtractRequest(
            os.path.abspath(directory), self.make_folder.IsChecked(), self._conflicts[max(0, self.conflict.GetSelection())])
        event.Skip()

    def result(self):
        return self._request


class PasswordWindow(viewkit.SubWindow):
    """書庫のパスワードを入力するウィンドウ。parameters は説明の文字列。結果は入力された文字列。"""

    def __init__(self, parent, ctx, title, parameters: str):
        super().__init__(parent, ctx, title, parameters)
        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        creator.staticText(parameters)
        self.password, dummy = creator.inputbox(_("パスワード"), x=400, style=wx.BORDER_RAISED | wx.TE_PASSWORD)
        self.password.SetFocus()

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

    def _on_ok(self, event):
        password = self.password.GetValue()
        if password == "":
            simpleDialog.errorDialog(_("パスワードを入力してください。"), self)
            return
        if "\"" in password:
            simpleDialog.errorDialog(_("パスワードに「\"」は使えません。"), self)
            return
        event.Skip()

    def result(self):
        return self.password.GetValue()
