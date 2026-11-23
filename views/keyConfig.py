# -*- coding: utf-8 -*-
# Falcon key config view
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import viewkit
import wx

import globalVars
import keymap
import simpleDialog

TIMER_INTERVAL = 100


class KeyInputWindow(viewkit.SubWindow):
    """
    ショートカットキーを押して入力するウィンドウ。
    parametersにはキーフィルタを指定する。Noneならメインウィンドウのキーフィルタを使う。
    結果は入力されたキーの文字列。設定解除(キャンセル)された場合は None。
    """

    def __init__(self, parent, ctx, title, parameters=None):
        super().__init__(parent, ctx, title, parameters)
        # キーフィルタ未指定ならデフォルトとしてメインビューで設定されたキーフィルタを適用
        self.key_filter = parameters if parameters is not None else globalVars.app.main_window.menu.keymap.filter
        self.input_key = ""  # 取得した入力キー(結果)
        self.pressing_key = ""  # 押下中のキー

        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL, margin=20)
        creator.staticText(_("設定するには、使用したいキーの組み合わせを押します。\n設定を解除するには、Escキーを押します。"))
        self.key_name_text = creator.staticText("", sizer_flag=wx.ALIGN_CENTER | wx.ALL, margin=20)
        self.error_text = creator.staticText("", sizer_flag=wx.ALIGN_CENTER)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        self.cancel_button = footer.cancelbutton(_("設定解除"), self._on_cancel)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_timer)
        self.timer.StartOnce(TIMER_INTERVAL)

    def result(self):
        return self.input_key if self.input_key != "" else None

    def _on_timer(self, event):
        self.timer.Stop()

        # キーの判定
        hits = []
        key_names = self.key_filter.GetUsableKeys()
        if "WINDOWS" not in key_names:
            key_names.append("WINDOWS")
        for name in key_names:
            # マウス関連は利用不可
            code = keymap.str2key[name]
            if code <= 4:
                continue
            # カテゴリキーは取得不可、NumLockとCapsLockは押し下げ状態ではなく現在のON/OFFを返してしまうので
            if type(code) == wx.KeyCategoryFlags or name == "NUMLOCK" or name == "SCROLL":
                continue
            if wx.GetKeyState(code):
                hits.append(name)

        if hits:
            self.cancel_button.Disable()  # こうしないとEnterで反応してEnterがショートカットに使えない
            self.pressing_key = "+".join(hits)
            if len(self.input_key) < len(self.pressing_key):
                self.input_key = self.pressing_key
            self.key_name_text.SetLabel(self.input_key)
            self.panel.Layout()
        else:  # キーが放されたら前の入力を検証する
            self.cancel_button.Enable()
            if self.input_key != "" and self.input_key != "SPACE":
                if self.key_filter.Check(self.input_key):
                    self.EndModal(wx.ID_OK)  # 正しい入力なのでダイアログを閉じる
                    return
                self.error_text.SetLabel(self.key_filter.GetLastError())
                self.panel.Layout()
                simpleDialog.errorDialog(self.key_filter.GetLastError(), self)
                self.pressing_key = ""
                self.input_key = ""
        self.timer.Start(TIMER_INTERVAL)

    def _on_cancel(self, event):
        self.cancel_button.Disable()
        self.timer.Stop()
        self.input_key = ""
        self.EndModal(wx.ID_CANCEL)

    def Destroy(self):
        self.timer.Stop()
        return super().Destroy()
