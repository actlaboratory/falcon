# -*- coding: utf-8 -*-
# Falcon FileHash view
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import wx
import misc
import views.ViewCreator
from logging import getLogger
from views.baseDialog import *

hashTypes = [
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


class Dialog(BaseDialog):
    def __init__(self, fname):
        super().__init__("FileHashDialog")
        self.fileName = fname

    def Initialize(self):
        super().Initialize(self.app.hMainView.hFrame, _("ファイルハッシュの計算"))
        self.InstallControls()
        return True

    def InstallControls(self):
        """いろんなwidgetを設置する。"""

        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.sizer, wx.HORIZONTAL, 20)
        self.combo, static = self.creator.combobox(
            _("値の種類"), hashTypes, state=hashTypes.index('sha256'))
        self.calcButton = self.creator.okbutton(
            _("計算"), self.calcStart, sizerFlag=wx.ALIGN_CENTER_VERTICAL)

        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.sizer, wx.VERTICAL, 20)
        self.resultFeeld, self.static = self.creator.inputbox(
            _("結果"), x=450, style=wx.TE_READONLY)

        self.buttonArea = views.ViewCreator.BoxSizer(
            self.sizer, wx.HORIZONTAL, wx.ALIGN_RIGHT)
        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.buttonArea, wx.HORIZONTAL, 20)
        self.bClose = self.creator.cancelbutton(_("閉じる"), None)

    def calcStart(self, event):
        hash = misc.calcHash(self.fileName, self.combo.GetStringSelection())
        self.resultFeeld.SetValue(hash)
        self.resultFeeld.SetFocus()
