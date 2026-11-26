# -*- coding: utf-8 -*-
# Falcon transfer conflict view
# Note: All comments except these top lines will be written in Japanese.

"""貼り付けでアップロード・ダウンロードするときに、転送先に同じ名前の項目がある場合の扱いを選ぶウィンドウ"""

import viewkit
import wx

import remote_transfer

# 例として表示する名前の数
_MAX_NAMES = 5


class TransferConflictWindow(viewkit.SubWindow):
    """
    同じ名前の項目があるときの扱いを選ぶウィンドウ。
    parameters は転送先にある同じ名前の項目の名前のリスト。結果は remote_transfer.CONFLICT_*。
    """

    def __init__(self, parent, ctx, title, parameters: list):
        super().__init__(parent, ctx, title, parameters)
        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        names = "\n".join(parameters[:_MAX_NAMES])
        if len(parameters) > _MAX_NAMES:
            names += "\n" + _("ほか %(count)d件") % {"count": len(parameters) - _MAX_NAMES}
        creator.staticText(_("転送先に、同じ名前の項目が %(count)d件あります。\n%(names)s") % {"count": len(parameters), "names": names})
        self.conflict, dummy = creator.combobox(_("同じ名前の項目があるとき"), remote_transfer.get_conflict_names(), state=0)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"))
        footer.cancelbutton(_("キャンセル"))
        self.conflict.SetFocus()

    def result(self):
        return remote_transfer.CONFLICTS[max(0, self.conflict.GetSelection())]
