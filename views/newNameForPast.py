# -*- coding: utf-8 -*-
# Falcon new file naming view
# 同一ディレクトリに貼り付けしようとしたときに、名前を問い合わせるときのやつ
# Copyright (C) 2021 Yukio Nozawa <personal@nyanchangames.com>

import wx
import views.ViewCreator
from logging import getLogger
from views.baseDialog import *


class Dialog(BaseDialog):
    def __init__(self):
        super().__init__("newNameEditDialog")

    def Initialize(self, existingName):
        super().Initialize(self.app.hMainView.hFrame, _("新しい名前を入力"))
        self.InstallControls(existingName)
        return True

    def InstallControls(self, existingName):
        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.sizer, wx.VERTICAL, 20)
        self.iName, self.static = self.creator.inputbox(_("新しい名前"), x=400, defaultValue=existingName)

        self.buttonArea = views.ViewCreator.BoxSizer(
            self.sizer, wx.HORIZONTAL, wx.ALIGN_RIGHT)
        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.buttonArea, wx.HORIZONTAL, 20)
        self.bOk = self.creator.okbutton(_("ＯＫ"), None)
        self.bCancel = self.creator.cancelbutton(_("スキップ"), None)

    def GetData(self):
        return self.iName.GetLineText(0)
