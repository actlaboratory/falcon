# -*- coding: utf-8 -*-
# Falcon operation Selecter view
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import wx
import gettext
from logging import getLogger

from .baseDialog import *
import misc
import views.ViewCreator


class Dialog(BaseDialog):

    def __init__(self, message, info, choices, enableCancel=False):
        super().__init__("OperationSelecterDialog")
        self.message = message
        self.info = info
        self.choices = choices
        self.enableCancel = enableCancel

    def Initialize(self):
        if self.enableCancel:
            super().Initialize(self.app.hMainView.hFrame, _("ファイル操作確認"))
        else:
            super().Initialize(self.app.hMainView.hFrame, _("ファイル操作確認"), 0)
        self.InstallControls()
        return True

    def InstallControls(self):
        """いろんなwidgetを設置する。"""

        # 情報の表示
        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.sizer, wx.VERTICAL, 20)
        if self.message:
            self.creator.staticText(self.message)
        self.hListCtrl, static = self.creator.listCtrl(
            _("アイテム情報"), proportion=0, sizerFlag=wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, size=(
                600, 300), style=wx.LC_REPORT | wx.LC_NO_HEADER | wx.LC_SINGLE_SEL)

        i = 0
        for i in range(len(self.info[0])):
            self.hListCtrl.InsertColumn(i, "")

        # for elem in colums():
        #	if count(self.info[0])>i:
        #	self.hListCtrl.InsertColumn(i,elem)
        #	i+=1

        for elem in self.info:
            self.hListCtrl.Append(elem)

        # 処理の選択
        self.select = self.creator.radiobox(_("アクション"), list(
            self.choices.keys()), None, 0, wx.VERTICAL)
        self.check = self.creator.checkbox(_("以降も同様に処理する"), None, False)

        # ボタンエリア
        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.sizer, wx.HORIZONTAL, 20, "", wx.ALIGN_RIGHT)
        self.bOk = self.creator.okbutton(_("ＯＫ"), None)
        if self.enableCancel:
            self.bCancel = self.creator.cancelbutton(_("キャンセル"), None)

    def GetData(self):
        return {
            "response": self.choices[self.select.GetStringSelection()],
            "all": self.check.IsChecked()
        }


def GetMethod(request):
    methods = {
        "ALREADY_EXISTS": {
            _("上書きする"): "overwrite",
            _("スキップ"): "skip"
        },
        "OWN_SUB_DIR": {
            _("スキップ"): "SKIP",
            _("名前を変える"): "RENAME",
        }
    }
    return methods[request]
