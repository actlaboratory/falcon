# -*- coding: utf-8 -*-
# Falcon register originalAssociation view
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import wx
import os
import re
from logging import getLogger

from .baseDialog import *
import misc
import views.ViewCreator
from simpleDialog import dialog


class Dialog(BaseDialog):

    def __init__(self, config):
        super().__init__()
        self.config = config

    def Initialize(self):
        t = misc.Timer()
        self.identifier = "registOriginalAssociationDialog"  # このビューを表す文字列
        self.log = getLogger("falcon.%s" % self.identifier)
        self.log.debug("created")
        super().Initialize(self.app.hMainView.hFrame, _("拡張子の独自関連付け"))
        self.InstallControls()
        self.log.debug("Finished creating main view (%f seconds)" % t.elapsed)
        return True

    def InstallControls(self):
        """いろんなwidgetを設置する。"""
        element_array = ('element_1', 'element_2', 'element_4',
                         'element_3', 'element_5')
        combobox_1 = wx.ComboBox(self.panel, wx.ID_ANY, '選択してください',
                                 choices=element_array, style=wx.CB_DROPDOWN)
        print(combobox_1.GetHandle())
