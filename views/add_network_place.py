# -*- coding: utf-8 -*-
# Falcon add network place view
# Note: All comments except these top lines will be written in Japanese.

"""追加するネットワークの場所のリンク先と名前を入力するウィンドウ"""

import viewkit
import wx

import network_drive
import network_place
import simpleDialog


class AddNetworkPlaceRequest:
    """ネットワークの場所の追加の内容"""

    def __init__(self, name, target):
        self.name = name
        self.target = target


class AddNetworkPlaceWindow(viewkit.SubWindow):
    """
    追加するネットワークの場所のリンク先と名前を入力するウィンドウ。
    parameters はリンク先の初期値。結果は AddNetworkPlaceRequest。
    """

    def __init__(self, parent, ctx, title, parameters: str):
        super().__init__(parent, ctx, title, parameters)
        self._request = None

        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        self.target, dummy = creator.inputbox(
            _("フォルダ（\\\\サーバー名\\共有名 の形式）"), default_value=parameters,
            x=400, style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
        self.target.hideScrollBar(wx.HORIZONTAL)
        self.name, dummy = creator.inputbox(
            _("名前（空欄なら自動で付けます）"), x=400, style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
        self.name.hideScrollBar(wx.HORIZONTAL)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

    def _on_ok(self, event):
        target = network_drive.normalize_remote_path(self.target.GetLineText(0))
        error = network_drive.validate_folder_path(target, allow_server=True)
        if error:
            simpleDialog.errorDialog(error, self)
            self.target.SetFocus()
            return
        name = self.name.GetLineText(0).strip()
        if name == "":
            name = network_place.make_unique_name(network_place.get_default_name(target))
        error = network_place.validate_name(name)
        if error:
            simpleDialog.errorDialog(error, self)
            self.name.SetFocus()
            return
        self._request = AddNetworkPlaceRequest(name, target)
        event.Skip()

    def result(self):
        return self._request
