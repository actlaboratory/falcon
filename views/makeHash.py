# -*- coding: utf-8 -*-
# Falcon FileHash view
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import viewkit
import wx

import misc

HASH_TYPES = [
    'md5',
    'sha1',
    'sha224',
    'sha256',
    'sha384',
    'sha512',
    'sha3_224',
    'sha3_256',
    'sha3_384',
    'sha3_512',
    'blake2s',
    'blake2b'
]


class MakeHashWindow(viewkit.SubWindow):
    """ファイルのハッシュ値を計算するウィンドウ。parametersは対象ファイルのパス。"""

    def __init__(self, parent, ctx, title, parameters: str):
        super().__init__(parent, ctx, title, parameters)
        creator = self.creator.makeChild(wx.HORIZONTAL, 20)
        self.hash_type, dummy = creator.combobox(_("値の種類"), HASH_TYPES, state=HASH_TYPES.index('sha256'))
        calc_button = creator.button(_("計算"), self._on_calc, sizer_flag=wx.ALIGN_CENTER_VERTICAL)
        calc_button.SetDefault()

        creator = self.creator.makeChild(wx.VERTICAL, 20)
        self.result_field, dummy = creator.inputbox(_("結果"), x=450, style=wx.TE_READONLY)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.cancelbutton(_("閉じる"))

    def _on_calc(self, event):
        self.result_field.SetValue(misc.calcHash(self.parameters, self.hash_type.GetStringSelection()))
        self.result_field.SetFocus()
