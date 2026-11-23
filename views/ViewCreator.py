# -*- coding: utf-8 -*-
# View Creator
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Copyright (C) 2019-2020 Hiroki Fujii <hfujii@hisystron.com>

# 画面部品の生成はviewkitのViewCreatorを利用する。
# このモジュールでは、falcon固有の設定(フォント・独自リストコントロール)を適用したViewCreatorを提供する。

import wx

from viewkit.creator import viewCreator
from viewkit.creator.viewCreator import *  # BoxSizer, GridBagSizer, makePanel, MODE_* などの定数・関数を公開する
from views import fontManager
from views.viewObjects import FalconVirtualListCtrl


class ViewCreator(viewCreator.ViewCreator):
    def __init__(self, mode, parent, parent_sizer=None, *pArg, **kArg):
        """
        ViewCreator

        :param int mode: Set view mode.
        :param wx.Window parent: Set parent window.
        :param wx.Sizer parent_sizer: Set parent sizer. Default is None.
        :param flag orient: Set Set widget layout. Default is wx.HORIZONTAL.
        :param int space: Set gap between items. Default is 0.
        :param str/int label: Set item label(str) or grid sizer's column count(int).
        :param flags style: Set sizer flags.
        :param int proportion: Set proportion.
        :param int margin: Set viewCreator's margin.
        """
        # フォントは設定ファイルの内容から生成する
        font = fontManager.FontManager().GetFont()
        super().__init__(mode, font, parent, parent_sizer, *pArg, **kArg)

        # 標準オブジェクトの変更が必要ならば記述
        # self.winObject["object_name"] = newObject
        self.winObject["virtualListCtrl"] = FalconVirtualListCtrl.FalconVirtualListCtrl

    @staticmethod
    def config2modeValue(color="white", wrapping="off"):
        """configから読み取った値からmodeの整数値を生成して返す"""
        if type(color) != str or type(wrapping) != str:
            raise ValueError
        mode = 0
        if color.lower() == "dark":
            mode += MODE_DARK
        if wrapping.lower() == "on":
            mode += MODE_WRAPPING
        return mode
