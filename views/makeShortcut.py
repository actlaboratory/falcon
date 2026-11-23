# -*- coding: utf-8 -*-
# Falcon make Shortcut view
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import viewkit
import wx

TYPE_LNK = 0
TYPE_HARDLINK = 1
TYPE_SYNLINK = 2

TYPE_STRINGS = {
    TYPE_LNK: "shortcut",
    TYPE_HARDLINK: "hardLink",
    TYPE_SYNLINK: "symbolicLink",
}

LINK_ABSOLUTE = 0
LINK_RELATIVE = 1


class MakeShortcutParameters:
    """MakeShortcutWindow に渡すパラメータ"""

    def __init__(self, target_name: str, can_make_lnk=True, can_make_hard_link=True, can_make_syn_link=True):
        if not can_make_lnk and not can_make_syn_link and not can_make_hard_link:
            raise ValueError(_("makeShortcutDialogを表示するには、少なくとも１種類のショートカットの作成が有効化されている必要があります。"))
        # 作成先初期値を決めるための、対象オブジェクトの拡張子を除く名前
        self.target_name = target_name
        self.can_make_lnk = can_make_lnk
        self.can_make_hard_link = can_make_hard_link
        self.can_make_syn_link = can_make_syn_link


class MakeShortcutWindow(viewkit.SubWindow):
    """ショートカットを作成するウィンドウ。結果は作成内容の辞書。"""

    def __init__(self, parent, ctx, title, parameters: MakeShortcutParameters):
        super().__init__(parent, ctx, title, parameters)
        # ここを並び替えるとこのクラス内の色んな所に影響するので注意！
        type_choices = [_("ショートカット(lnk)"), _("ハードリンク"), _("シンボリックリンク")]

        main_area = self.creator.makeChild(wx.HORIZONTAL, 0, style=wx.ALIGN_CENTER)

        # 種類の設定
        type_creator = main_area.makeChild(wx.VERTICAL, 20)
        self.type = type_creator.radiobox(_("作成方式"), type_choices, self._on_type_changed, 1, wx.VERTICAL)
        self.type.EnableItem(TYPE_LNK, parameters.can_make_lnk)
        self.type.EnableItem(TYPE_HARDLINK, parameters.can_make_hard_link)
        self.type.EnableItem(TYPE_SYNLINK, parameters.can_make_syn_link)

        # 詳細設定
        detail_creator = main_area.makeChild(wx.VERTICAL, 20)
        self.parameter, dummy = detail_creator.inputbox(_("パラメータ"), x=400)
        self.directory, dummy = detail_creator.inputbox(_("作業ディレクトリ"), x=400)
        self.link_type = detail_creator.radiobox(_("リンクの種類"), [_("絶対"), _("相対")], None, 1, wx.HORIZONTAL)

        # 作成先
        destination_creator = self.creator.makeChild(wx.HORIZONTAL, 0, "", wx.EXPAND)
        self.destination, dummy = destination_creator.inputbox(_("作成先") + "：", x=-1, default_value=parameters.target_name + ".lnk")

        # ボタンエリア
        footer = self.creator.makeChild(wx.HORIZONTAL, 20, "", wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"))
        footer.cancelbutton(_("キャンセル"))

    def result(self):
        v = {}
        v["type"] = TYPE_STRINGS[self.type.GetSelection()]
        v["destination"] = self.destination.GetLineText(0)
        v["parameter"] = self.parameter.GetLineText(0)
        v["directory"] = self.directory.GetLineText(0)
        if not v["type"] == TYPE_HARDLINK:
            v["linkType"] = self.link_type.GetSelection()
        return v

    def _on_type_changed(self, event):
        """作成するショートカットタイプの変更"""
        if event.GetInt() == TYPE_HARDLINK:
            # ハードリンクに絶対・相対の選択はない
            self.link_type.Disable()
        else:
            # ハードリンク以外であれば絶対・相対の選択がある
            self.link_type.Enable()

        # パラメータとディレクトリの指定はlnkだけ
        if event.GetInt() == TYPE_LNK:
            self.parameter.Enable()
            self.directory.Enable()
        else:
            self.parameter.Disable()
            self.directory.Disable()
