# -*- coding: utf-8 -*-
# Falcon change file attribute view
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import viewkit
import wx


class ChangeAttributeWindow(viewkit.SubWindow):
    """
    ファイルの属性を変更するウィンドウ。
    parametersは現在の属性(読み取り専用・隠し・システム・アーカイブ)のチェック状態のリスト。
    結果は変更後のチェック状態のリスト。
    """

    def __init__(self, parent, ctx, title, parameters: list):
        super().__init__(parent, ctx, title, parameters)
        # 属性の変更
        creator = self.creator.makeChild(wx.VERTICAL, 20, _("属性の変更"))
        self.checks = creator.checkbox3([_("読み取り専用"), _("隠し"), _("システム"), _("アーカイブ")], None, parameters)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20)
        footer.okbutton(_("ＯＫ"))
        footer.cancelbutton(_("キャンセル"))

    def result(self):
        return [check.Get3StateValue() for check in self.checks]
