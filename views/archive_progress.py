# -*- coding: utf-8 -*-
# Falcon archive progress view
# Note: All comments except these top lines will be written in Japanese.

"""圧縮・解凍の進み具合を表示するウィンドウ"""

import viewkit
import wx

import archiver

# 進み具合を調べる間隔(ミリ秒)
_INTERVAL = 200


class ArchiveProgressWindow(viewkit.SubWindow):
    """圧縮・解凍の進み具合を表示し、終わったら自動で閉じるウィンドウ。parameters は実行中の archiver.Job。"""

    def __init__(self, parent, ctx, title, parameters: archiver.Job):
        super().__init__(parent, ctx, title, parameters)
        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        self.gauge, dummy = creator.gauge(_("進行状況"), x=400)
        self.gauge.SetRange(100)
        self.cancel_button = creator.button(_("中止"), self._on_cancel)
        self.cancel_button.SetFocus()
        # Escキーでも中止できるようにする
        self.Bind(wx.EVT_CHAR_HOOK, self._on_key)
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_timer, self._timer)
        self._timer.Start(_INTERVAL)

    def _on_key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self._cancel()
        else:
            event.Skip()

    def _on_cancel(self, event):
        self._cancel()

    def _cancel(self):
        """中止を指示する。実際に止まったら、タイマーの処理で閉じる。"""
        self.cancel_button.SetLabel(_("中止しています"))
        self.parameters.cancel()

    def _on_timer(self, event):
        if self.parameters.is_finished():
            if self.IsModal():
                self._timer.Stop()
                self.EndModal(wx.ID_OK)
            return
        if self.gauge.GetValue() != self.parameters.percentage:
            self.gauge.SetValue(self.parameters.percentage)
