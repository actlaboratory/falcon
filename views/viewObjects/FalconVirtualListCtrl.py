
import os

import wx

import browsableObjects
import globalVars

from viewkit.creator.objects import virtual_listctrl


class FalconVirtualListCtrl(virtual_listctrl.virtualListCtrl):
    def __init__(self, *pArg, **kArg):
        super().__init__(*pArg, **kArg)

    def OnGetItemText(self, item, column):
        """表示する文字列を返す。設定に応じて、ファイル名の拡張子を取り除く。"""
        text = super().OnGetItemText(item, column)
        # 検索やファイル操作に影響しないよう、項目が持つ名前は変えず、表示だけを変える
        if self.getColFromWx(column).col != 0:
            return text
        elem = self.lst[item]
        if not isinstance(elem, browsableObjects.File) or isinstance(elem, browsableObjects.Folder):
            return text
        if not globalVars.app.settings.get_bool("view", "hide_extension", False):
            return text
        return os.path.splitext(text)[0]

    def GetItemBackgroundColour(self, item, colour):
        return self.lst[item].list_backgroundColour

    def SetItemBackgroundColour(self, item, colour):
        self.lst[item].list_backgroundColour = colour

    def SetItemImage(self, item, image, selImage=-1):
        self.lst[item].list_imageIndex = image

    def OnGetItemAttr(self, item):
        ret = self.lst[item]
        if type(ret) == list:
            return None
        else:
            ret = ret.list_backgroundColour
            if ret:
                self.CheckedItemAttr = wx.ItemAttr()
                self.CheckedItemAttr.SetBackgroundColour(wx.Colour(ret))
                return self.CheckedItemAttr
            return None

    def OnGetItemImage(self, item):
        if type(self.lst[item]) == list:
            return -1
        else:
            return self.lst[item].list_imageIndex
