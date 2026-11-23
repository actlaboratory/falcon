# -*- coding: utf-8 -*-
# Simple input dialog view
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import re

import viewkit
import wx


class SimpleInputParameters:
    """SimpleInputWindow に渡すパラメータ"""

    def __init__(self, detail: str, default_value: str = "", validation_pattern: str = None):
        self.detail = detail
        self.default_value = default_value
        self.validation_pattern = validation_pattern


class SimpleInputWindow(viewkit.SubWindow):
    """1行の文字列を入力するウィンドウ。結果は入力された文字列。"""

    def __init__(self, parent, ctx, title, parameters: SimpleInputParameters):
        super().__init__(parent, ctx, title, parameters)
        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        self.edit, dummy = creator.inputbox(parameters.detail, default_value=parameters.default_value, x=-1,
                                            style=wx.BORDER_RAISED | wx.TE_DONTWRAP, sizer_flag=wx.EXPAND)
        self.edit.hideScrollBar(wx.HORIZONTAL)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

    def _on_ok(self, event):
        pattern = self.parameters.validation_pattern
        if pattern and not re.fullmatch(pattern, self.edit.GetLineText(0)):
            return
        event.Skip()

    def result(self):
        return self.edit.GetLineText(0)
