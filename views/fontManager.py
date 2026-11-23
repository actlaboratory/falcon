# -*- coding: utf-8 -*-
# Copyright (C) 2019 yamahubuki <itiro.ishino@gmail.com>

"""
falconの画面で使うフォントを管理する。
フォントの設定は viewkit の設定(view.font)に保存し、表示する文字列の解釈は viewkit の FontManager に任せる。
"""

import viewkit.fontManager
import wx

from logging import getLogger

import constants
import globalVars
from simpleDialog import dialog


class FontManager(viewkit.fontManager.FontManager):
    def __init__(self):
        super().__init__()
        self.log = getLogger("%s.FontManager" % constants.LOG_PREFIX)
        app = globalVars.app
        if app is None:
            return
        # 設定ファイルの情報を基にfontを生成
        settings = app.ctx.settings
        font_string = settings.getSetting("view.font", "")
        if font_string and not self.setFontFromString(font_string):
            dialog(_("エラー"), _("設定されているフォント情報が不正です。デフォルトのフォントを適用します。"))
            settings.changeSetting("view.font", viewkit.fontManager.DEFAULT_FONT)

    def show_setting_dialog(self, parent):
        """フォント設定ダイアログを表示し、選ばれたフォントを設定に保存する"""
        if not self.showSettingDialog(parent):
            return False
        globalVars.app.ctx.settings.changeSetting("view.font", self.getInfo())
        return True

    def showSettingDialog(self, parent):
        # viewkitの実装はキャンセル時に例外となるため、falcon側で実装する
        font_data = wx.FontData()
        font_data.EnableEffects(False)  # 取り消し線などは設定できない
        font_data.SetAllowSymbols(False)  # シンボルフォントの設定は認めない
        font_data.SetRange(constants.FONT_MIN_SIZE, constants.FONT_MAX_SIZE)
        font_data.SetInitialFont(self.font)

        font_chooser = wx.FontDialog(parent, font_data)
        if font_chooser.ShowModal() != wx.ID_OK:
            self.log.info("font change was canceled.")
            font_chooser.Destroy()
            return False
        font = font_chooser.GetFontData().GetChosenFont()
        font_chooser.Destroy()
        # アサーションエラーの対策
        if not font.IsOk():
            dialog(_("エラー"), _("原因不明のエラーにより、フォントの変更に失敗しました。"))
            self.log.warning("font change error. IsOK() returned False.")
            return False
        self.font = font
        return True
