# -*- coding: utf-8 -*-
# Falcon make new file view
# Note: All comments except these top lines will be written in Japanese.

"""新しいファイルの名前と種類を入力するウィンドウ"""

import viewkit
import wx

import new_file
import simpleDialog


class NewFileWindow(viewkit.SubWindow):
    """
    作成するファイルの名前と種類を入力するウィンドウ。
    parameters は作成先のディレクトリのフルパス。
    結果は new_file.NewFileRequest。
    """

    def __init__(self, parent, ctx, title, parameters: str):
        super().__init__(parent, ctx, title, parameters)
        self._file_types = new_file.get_file_types()

        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        self.name, dummy = creator.inputbox(
            _("ファイル名"), x=400, style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
        self.name.hideScrollBar(wx.HORIZONTAL)
        self.file_type, dummy = creator.combobox(
            _("種類（名前に拡張子がなければ付けます）"), [t.label() for t in self._file_types],
            state=new_file.get_default_index(self._file_types), x=400)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

    def _selected_type(self):
        """選ばれているファイルの種類を返す"""
        index = self.file_type.GetSelection()
        if index < 0:
            index = 0
        return self._file_types[index]

    def _make_name(self):
        """入力内容から作成するファイル名を作る"""
        name = self.name.GetLineText(0)
        file_type = self._selected_type()
        if name.strip() == "":
            return new_file.make_default_name(self.parameters, file_type)
        return new_file.make_name(name, file_type)

    def _on_ok(self, event):
        error = new_file.validate(self.parameters, self._make_name())
        if error != "":
            simpleDialog.errorDialog(error, self)
            self.name.SetFocus()
            return
        event.Skip()

    def result(self):
        return new_file.NewFileRequest(self._make_name(), self._selected_type())
