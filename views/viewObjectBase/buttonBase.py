# buttonBase for ViewCreator
# Copyright (C) 2019-2020 Hiroki Fujii <hfujii@hisystron.com>


import wx
from views.viewObjectBase import viewObjectUtil, toolTipBase, controlBase


class button(controlBase.controlBase, wx.Button):
    def __init__(self, *pArg, **kArg):
        self.focusFromKbd = viewObjectUtil.popArg(
            kArg, "enableTabFocus", True)  # キーボードフォーカスの初期値
        super().__init__(*pArg, **kArg)
        self.Bind(wx.EVT_ENTER_WINDOW, self.onMouseEnter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.onMouseLeave)
        # ツールチップ
        self.toolTipObject = toolTipBase.toolTip  # ツールチップオブジェクトを指定
        self.enableToolTip = False

    def setToolTip(self, label=None):
        """
        ツールチップをセット、またはチップラベルを変更します。

        :param str/None label: ラベル。デフォルトはボタンラベルと同期
        """
        self.toolTipLabel = label
        if not self.enableToolTip:
            self.enableToolTip = True
            self.toolTip = None
        elif self.enableToolTip and self.toolTip is not None:
            if self.toolTipLabel is None:
                self.toolTip.refresh(label=self.Label)
            else:
                self.toolTip.refresh(label=self.toolTipLabel)

    def onMouseEnter(self, evt):
        if self.enableToolTip and self.toolTip is None:
            if self.toolTipLabel is None:
                self.toolTip = self.toolTipObject(
                    self,
                    self.ClientToScreen(
                        evt.GetPosition()),
                    self.Label,
                    self.GetBackgroundColour(),
                    self.GetForegroundColour(),
                    self.GetFont())
            else:
                self.toolTip = self.toolTipObject(
                    self,
                    self.ClientToScreen(
                        evt.GetPosition()),
                    self.toolTipLabel,
                    self.GetBackgroundColour(),
                    self.GetForegroundColour(),
                    self.GetFont())

    def onMouseLeave(self, evt):
        if self.enableToolTip and self.toolTip is not None:
            self.toolTip.destroy()
            self.toolTip = None
