# -*- coding: utf-8 -*-
# Falcon compare tabs view
# Note: All comments except these top lines will be written in Japanese.

"""「フォルダの比較」で、比較先のタブを選ぶウィンドウ"""

import viewkit
import wx


class CompareTabsWindow(viewkit.SubWindow):
    """比べる相手のタブを選ぶウィンドウ。parameters はタブの表示名のリスト。結果は選んだタブの番号"""

    def __init__(self, parent, ctx, title, parameters: list):
        super().__init__(parent, ctx, title, parameters)
        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        self.target, dummy = creator.combobox(_("比較先"), parameters, state=0, x=400)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"))
        footer.cancelbutton(_("キャンセル"))
        self.target.SetFocus()

    def result(self):
        return max(0, self.target.GetSelection())
