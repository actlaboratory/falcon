# -*- coding: utf-8 -*-
# Falcon map network drive view
# Note: All comments except these top lines will be written in Japanese.

"""ネットワークドライブの割り当ての内容を入力するウィンドウ"""

import viewkit
import wx

import network_drive
import simpleDialog


class MapNetworkDriveParameters:
    """MapNetworkDriveWindow に渡す値"""

    def __init__(self, letters, remote_path=""):
        # 選べるドライブ文字の一覧（"Z" など）
        self.letters = letters
        # フォルダの初期値
        self.remote_path = remote_path


class MapNetworkDriveWindow(viewkit.SubWindow):
    """
    割り当てるドライブ文字とフォルダを入力するウィンドウ。
    parameters は MapNetworkDriveParameters。結果は network_drive.MapRequest。
    """

    def __init__(self, parent, ctx, title, parameters: MapNetworkDriveParameters):
        super().__init__(parent, ctx, title, parameters)
        self._request = None

        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        self.letter, dummy = creator.combobox(
            _("ドライブ"), ["%s:" % letter for letter in parameters.letters], state=0)
        self.remote_path, dummy = creator.inputbox(
            _("フォルダ（\\\\サーバー名\\共有名 の形式）"), default_value=parameters.remote_path,
            x=400, style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
        self.remote_path.hideScrollBar(wx.HORIZONTAL)
        self.reconnect = creator.checkbox(_("サインイン時に再接続する"), state=True)
        self.use_other_credentials = creator.checkbox(_("別の資格情報を使用して接続する"), state=False)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))
        # ドライブ文字は最初の候補のままでよいことが多いので、フォルダの入力から始める
        self.remote_path.SetFocus()

    def _on_ok(self, event):
        path = network_drive.normalize_remote_path(self.remote_path.GetLineText(0))
        error = network_drive.validate_folder_path(path)
        if error:
            simpleDialog.errorDialog(error, self)
            self.remote_path.SetFocus()
            return
        letter = self.parameters.letters[self.letter.GetSelection()]
        self._request = network_drive.MapRequest(
            letter, path, self.reconnect.GetValue(), self.use_other_credentials.GetValue())
        event.Skip()

    def result(self):
        return self._request
