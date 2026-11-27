# -*- coding: utf-8 -*-
# Falcon download view
# Note: All comments except these top lines will be written in Japanese.

"""FTP・SFTP のサーバーからダウンロードするときの保存先を入力するウィンドウ"""

import os

import viewkit
import wx

import remote_transfer
import simpleDialog


class DownloadWindow(viewkit.SubWindow):
    """
    保存先のフォルダと、同じ名前の項目があるときの扱いを入力するウィンドウ。
    parameters は保存先の初期値。結果は (保存先のフォルダ, remote_transfer.CONFLICT_*)。
    """

    def __init__(self, parent, ctx, title, parameters: str):
        super().__init__(parent, ctx, title, parameters)
        self._result = None
        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        directory_creator = creator.makeChild(wx.HORIZONTAL, 0, "", wx.ALL | wx.EXPAND, margin=0)
        self.directory, dummy = directory_creator.inputbox(
            _("保存先のフォルダ"), default_value=parameters, x=400, style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
        self.directory.hideScrollBar(wx.HORIZONTAL)
        directory_creator.button(_("参照"), self._on_browse)
        self.conflict, dummy = creator.combobox(
            _("既存の項目の処理"), remote_transfer.get_conflict_names(), state=0)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

    def _on_browse(self, event):
        d = wx.DirDialog(self, _("保存先のフォルダの選択"), defaultPath=self.directory.GetLineText(0))
        if d.ShowModal() != wx.ID_CANCEL:
            self.directory.SetValue(d.GetPath())
        d.Destroy()
        self.directory.SetFocus()

    def _on_ok(self, event):
        directory = os.path.expandvars(self.directory.GetLineText(0).strip().strip("\""))
        if not os.path.isabs(directory) or os.path.isfile(directory):
            simpleDialog.errorDialog(_("保存先には絶対パスを指定してください。"), self)
            self.directory.SetFocus()
            return
        self._result = (os.path.abspath(directory), remote_transfer.CONFLICTS[max(0, self.conflict.GetSelection())])
        event.Skip()

    def result(self):
        return self._result
