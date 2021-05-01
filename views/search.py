# -*- coding: utf-8 -*-
# Falcon search view
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import wx
from logging import getLogger, FileHandler, Formatter
from .baseDialog import *
import views.ViewCreator

from simpleDialog import dialog


class Dialog(BaseDialog):

    # 検索の起点を設定
    def __init__(self, basePath, searchHistory, grepHistory):
        super().__init__("SearchDialog")
        self.basePath = basePath
        self.searchHistory = searchHistory
        self.grepHistory = grepHistory

    def Initialize(self):
        super().Initialize(self.app.hMainView.hFrame, _("検索"))
        self.InstallControls()
        return True

    def InstallControls(self):
        """いろんなwidgetを設置する。"""
        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.sizer, wx.HORIZONTAL, 20, "", wx.EXPAND)
        self.keyword, tmp = self.creator.comboEdit(
            _("キーワード") + "：", self.searchHistory, None, "", x=500)

        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.sizer, wx.HORIZONTAL, 20, "", wx.EXPAND)
        self.type = self.creator.radiobox(
            _("検索方式"), (_("ファイル名"), _("ファイル内容")), self.changeType, 1, wx.HORIZONTAL)
        self.keywordType = self.creator.checkbox(_("正規表現を利用"), None, False)

        # ボタンエリア
        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.sizer, wx.HORIZONTAL, 20, "", wx.ALIGN_RIGHT)
        self.bOk = self.creator.okbutton(_("ＯＫ"), self.OkEvent)
        self.bCancel = self.creator.cancelbutton(_("キャンセル"), None)

    def GetData(self):
        v = {}
        v["basePath"] = self.basePath
        v["keyword"] = self.keyword.GetValue()
        v["type"] = self.type.GetSelection()
        v["isRegularExpression"] = self.keywordType.IsChecked()
        return v

    def changeType(self, event):
        if event.GetSelection() == 0:
            self.keyword.Set(self.searchHistory)
        else:
            self.keyword.Set(self.grepHistory)

    def OkEvent(self, event):
        if self.keyword.GetValue() == "":
            dialog(_("エラー"), "検索キーワードを入力してください。")
            return
        event.Skip()
