
import wx

from views.viewObjectBase import virtualListCtrlBase


class FalconVirtualListCtrl(virtualListCtrlBase.virtualListCtrl):
    def __init__(self, *pArg, **kArg):
        super().__init__(*pArg, **kArg)

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
