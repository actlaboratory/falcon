# -*- coding: utf-8 -*-
# Falcon search view
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import viewkit
import wx

import misc

from simpleDialog import dialog

SEARCH_TYPE_FILE_NAME = 0
SEARCH_TYPE_FILE_CONTENT = 1


class SearchParameters:
    """SearchWindow に渡すパラメータ"""

    def __init__(self, base_path: str, search_history: list, grep_history: list):
        self.base_path = base_path
        self.search_history = search_history
        self.grep_history = grep_history


class SearchWindow(viewkit.SubWindow):
    """検索条件を入力するウィンドウ。結果は検索条件の辞書。"""

    def __init__(self, parent, ctx, title, parameters: SearchParameters):
        super().__init__(parent, ctx, title, parameters)
        creator = self.creator.makeChild(wx.HORIZONTAL, 20, "", wx.EXPAND)
        self.keyword, dummy = creator.comboEdit(_("キーワード") + "：", parameters.search_history, None, "", x=500)

        creator = self.creator.makeChild(wx.HORIZONTAL, 20, "", wx.EXPAND)
        self.type = creator.radiobox(_("検索方式"), (_("ファイル名"), _("ファイル内容")), self._on_type_changed, 1, wx.HORIZONTAL)
        self.regular_expression = creator.checkbox(_("正規表現を利用"), None, False)

        # ボタンエリア
        footer = self.creator.makeChild(wx.HORIZONTAL, 20, "", wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

    def result(self):
        return {
            "basePath": self.parameters.base_path,
            "keyword": self.keyword.GetValue(),
            "type": self.type.GetSelection(),
            "isRegularExpression": self.regular_expression.IsChecked(),
        }

    def _on_type_changed(self, event):
        if event.GetSelection() == SEARCH_TYPE_FILE_NAME:
            self.keyword.Set(self.parameters.search_history)
        else:
            self.keyword.Set(self.parameters.grep_history)

    def _on_ok(self, event):
        keyword = self.keyword.GetValue()
        if keyword == "":
            dialog(_("エラー"), _("検索キーワードを入力してください。"), self)
            return
        if self.regular_expression.IsChecked():
            ret = misc.ValidateRegularExpression(keyword)
            if ret != "OK":
                dialog(_("エラー"), _("正規表現の文法が間違っています。\nエラー内容: %(error)s") % {'error': ret}, self)
                return
        event.Skip()
