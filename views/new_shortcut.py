# -*- coding: utf-8 -*-
# Falcon make new shortcut view
# Note: All comments except these top lines will be written in Japanese.

"""新しいショートカットのリンク先と名前を入力するウィンドウ"""

import viewkit
import wx

import new_shortcut
import simpleDialog


class NewShortcutWindow(viewkit.SubWindow):
    """
    作成するショートカットのリンク先と名前を入力するウィンドウ。
    parameters は作成先のディレクトリのフルパス。
    結果は new_shortcut.NewShortcutRequest。
    """

    def __init__(self, parent, ctx, title, parameters: str):
        super().__init__(parent, ctx, title, parameters)
        self._request = None

        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        target_creator = creator.makeChild(wx.HORIZONTAL, 0, "", wx.ALL | wx.EXPAND, margin=0)
        self.target, dummy = target_creator.inputbox(
            _("リンク先（ファイル・フォルダのパス、または URL）"), x=400, style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
        self.target.hideScrollBar(wx.HORIZONTAL)
        target_creator.button(_("ファイルを参照"), self._on_browse_file)
        target_creator.button(_("フォルダを参照"), self._on_browse_dir)
        self.name, dummy = creator.inputbox(
            _("名前（空欄なら自動で付けます）"), x=400, style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
        self.name.hideScrollBar(wx.HORIZONTAL)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

    def _on_browse_file(self, event):
        d = wx.FileDialog(self, _("リンク先のファイルを選択"), defaultDir=self.parameters,
                          style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_SHOW_HIDDEN | wx.FD_NO_FOLLOW)
        if d.ShowModal() != wx.ID_CANCEL:
            self.target.SetValue(d.GetPath())
        d.Destroy()
        self.target.SetFocus()

    def _on_browse_dir(self, event):
        d = wx.DirDialog(self, _("リンク先のフォルダを選択"), defaultPath=self.parameters)
        if d.ShowModal() != wx.ID_CANCEL:
            self.target.SetValue(d.GetPath())
        d.Destroy()
        self.target.SetFocus()

    def _on_ok(self, event):
        try:
            self._request = new_shortcut.make_request(
                self.parameters, self.target.GetLineText(0), self.name.GetLineText(0))
        except ValueError as e:
            simpleDialog.errorDialog(str(e), self)
            self.target.SetFocus()
            return
        event.Skip()

    def result(self):
        return self._request
