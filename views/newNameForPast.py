# -*- coding: utf-8 -*-
# Falcon new file naming view
# 同一ディレクトリに貼り付けしようとしたときに、名前を問い合わせるときのやつ
# Copyright (C) 2021 Yukio Nozawa <personal@nyanchangames.com>

import viewkit
import wx


class NewNameForPastWindow(viewkit.SubWindow):
    """貼り付け先の新しい名前を入力するウィンドウ。parametersは既存の名前。結果は入力された名前。"""

    def __init__(self, parent, ctx, title, parameters: str):
        super().__init__(parent, ctx, title, parameters)
        creator = self.creator.makeChild(wx.VERTICAL, 20)
        self.name_edit, dummy = creator.inputbox(_("新しい名前"), x=400, default_value=parameters)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"))
        footer.cancelbutton(_("スキップ"))

    def result(self):
        return self.name_edit.GetLineText(0)
