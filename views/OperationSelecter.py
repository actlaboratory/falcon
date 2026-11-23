# -*- coding: utf-8 -*-
# Falcon operation Selecter view
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import viewkit
import wx


class OperationSelecterParameters:
    """
    OperationSelecterWindow に渡すパラメータ。
    info は表示する情報(各行のタプル)のリスト、choices は {表示名: レスポンス文字列} の辞書。
    """

    def __init__(self, message: str, info: list, choices: dict, enable_cancel: bool = False):
        self.message = message
        self.info = info
        self.choices = choices
        self.enable_cancel = enable_cancel


class OperationSelecterWindow(viewkit.SubWindow):
    """ファイル操作の確認(上書きするかどうかなど)を行うウィンドウ。結果は {"response": レスポンス, "all": 以降も同様に処理するか} の辞書。"""

    def __init__(self, parent, ctx, title, parameters: OperationSelecterParameters):
        super().__init__(parent, ctx, title, parameters)
        # 情報の表示
        creator = self.creator.makeChild(wx.VERTICAL, 20)
        if parameters.message:
            creator.staticText(parameters.message)
        self.list_ctrl, dummy = creator.listCtrl(
            _("アイテム情報"), proportion=0, sizer_flag=wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, size=(600, 300),
            style=wx.LC_REPORT | wx.LC_NO_HEADER | wx.LC_SINGLE_SEL)
        for i in range(len(parameters.info[0])):
            self.list_ctrl.InsertColumn(i, "")
        for elem in parameters.info:
            self.list_ctrl.Append(elem)

        # 処理の選択
        self.select = creator.radiobox(_("アクション"), list(parameters.choices.keys()), None, 0, wx.VERTICAL)
        self.check = creator.checkbox(_("以降も同様に処理する"), None, False)

        # ボタンエリア
        footer = self.creator.makeChild(wx.HORIZONTAL, 20, "", wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"))
        if parameters.enable_cancel:
            footer.cancelbutton(_("キャンセル"))

    def result(self):
        return {
            "response": self.parameters.choices[self.select.GetStringSelection()],
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
