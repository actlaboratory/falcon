# -*- coding: utf-8 -*-
# Falcon make Shortcut view
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import wx
from logging import getLogger, FileHandler, Formatter
from .baseDialog import *
from simpleDialog import *
import views.ViewCreator


class Dialog(BaseDialog):

    TYPE_LNK = 0
    TYPE_HARDLINK = 1
    TYPE_SYNLINK = 2

    typeStrings = {}
    typeStrings[TYPE_LNK] = "shortcut"
    typeStrings[TYPE_HARDLINK] = "hardLink"
    typeStrings[TYPE_SYNLINK] = "symbolicLink"

    LINK_ABSOLUTE = 0
    LINK_RELATIVE = 1

    # 作成先初期値を決めるためのターゲットの名前、作成できないタイプがあれば指定
    def __init__(
            self,
            targetName,
            canMakeLnk=True,
            canMakeHardLink=True,
            canMakeSynLink=True):
        if not canMakeLnk and not canMakeSynLink and not canMakeHardLink:
            raise ValueError(
                _("makeShortcutDialogを表示するには、少なくとも１種類のショートカットの作成が有効化されている必要があります。"))
        super().__init__("MakeShortcutDialog")
        # 対象オブジェクトの拡張子を除く名前
        self.targetName = targetName
        self.canMakeLnk = canMakeLnk
        self.canMakeSynLink = canMakeSynLink
        self.canMakeHardLink = canMakeHardLink

    def Initialize(self):
        super().Initialize(self.app.hMainView.hFrame, _("ショートカットの作成"))
        self.InstallControls()
        return True

    def InstallControls(self):
        # ここを並び替えるとこのクラス内の色んな所に影響するので注意！
        _typeChoices = [_("ショートカット(lnk)"), _("ハードリンク"), _("シンボリックリンク")]

        """いろんなwidgetを設置する。"""
        self.mainArea = views.ViewCreator.BoxSizer(
            self.sizer, wx.HORIZONTAL, wx.ALIGN_CENTER)

        # 種類の設定
        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.mainArea, wx.VERTICAL, 20)
        self.type = self.creator.radiobox(
            _("作成方式"), _typeChoices, self.typeChangeEvent, 1, wx.VERTICAL)

        self.type.EnableItem(self.TYPE_LNK, self.canMakeLnk)
        self.type.EnableItem(self.TYPE_HARDLINK, self.canMakeHardLink)
        self.type.EnableItem(self.TYPE_SYNLINK, self.canMakeSynLink)

        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.sizer, wx.HORIZONTAL, 0, "", wx.EXPAND)
        self.destination, tmp = self.creator.inputbox(
            _("作成先") + "：", x=-1, defaultValue=self.targetName + ".lnk")

        # 詳細設定
        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.mainArea, wx.VERTICAL, 20)
        self.parameter, tmp = self.creator.inputbox(_("パラメータ"), x=400)
        self.directory, tmp = self.creator.inputbox(_("作業ディレクトリ"), x=400)
        self.linkType = self.creator.radiobox(
            _("リンクの種類"), [_("絶対"), _("相対")], None, 1, wx.HORIZONTAL)

        # ボタンエリア
        self.creator = views.ViewCreator.ViewCreator(
            1, self.panel, self.sizer, wx.HORIZONTAL, 20, "", wx.ALIGN_RIGHT)
        self.bOk = self.creator.okbutton(_("ＯＫ"), None)
        self.bCancel = self.creator.cancelbutton(_("キャンセル"), None)

    def GetData(self):
        v = {}
        v["type"] = self.typeStrings[self.type.GetSelection()]
        v["destination"] = self.destination.GetLineText(0)
        v["parameter"] = self.parameter.GetLineText(0)
        v["directory"] = self.directory.GetLineText(0)
        if not v["type"] == self.TYPE_HARDLINK:
            v["linkType"] = self.linkType.GetSelection()
        return v

    # 作成するショートカットタイプの変更
    def typeChangeEvent(self, event):
        if event.GetInt() == self.TYPE_HARDLINK:
            # ハードリンクに絶対・相対の選択はない
            self.linkType.Disable()
        else:
            # ハードリンク以外であれば絶対・相対の選択がある
            self.linkType.Enable()

        # パラメータとディレクトリの指定はlnkだけ
        if event.GetInt() == self.TYPE_LNK:
            self.parameter.Enable()
            self.directory.Enable()
        else:
            self.parameter.Disable()
            self.directory.Disable()
