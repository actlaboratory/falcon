# -*- coding: utf-8 -*-
# Falcon waiting view
# Note: All comments except these top lines will be written in Japanese.

"""時間のかかる処理が終わるのを待っていることを示すウィンドウ"""

import viewkit
import wx

# 処理が終わったかどうかを調べる間隔(ミリ秒)
_INTERVAL = 50


class WaitingWindow(viewkit.SubWindow):
    """処理が終わったら自動で閉じるウィンドウ。parameters は実行中の background_wait.Task。"""

    def __init__(self, parent, ctx, title, parameters):
        super().__init__(parent, ctx, title, parameters)
        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        creator.staticText(_("読み込んでいます。しばらくお待ちください。"))
        self.cancel_button = creator.button(_("中止"), self._on_cancel)
        self.cancel_button.SetFocus()
        # Escキーでも中止できるようにする
        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_timer, self._timer)
        self._timer.Start(_INTERVAL)

    def _on_key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self._close(wx.ID_CANCEL)
        else:
            event.Skip()

    def _on_cancel(self, event):
        self._close(wx.ID_CANCEL)

    def _on_timer(self, event):
        if self.parameters.is_finished():
            self._close(wx.ID_OK)

    def _close(self, code):
        """ウィンドウを閉じる。中止のときも、処理が止まるのは待たない。"""
        if not self.IsModal():
            return
        self._timer.Stop()
        if code == wx.ID_CANCEL:
            self.parameters.cancel()
        self.EndModal(code)
