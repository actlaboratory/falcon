# -*- coding: utf-8 -*-
# Falcon remote login view
# Note: All comments except these top lines will be written in Japanese.

"""FTP・SFTP のサーバーに接続するときのユーザー名とパスワードを入力するウィンドウ"""

import viewkit
import wx

import remote_storage
import simpleDialog


class RemoteLoginParameters:
    """RemoteLoginWindow に渡す値"""

    def __init__(self, message, user="", user_editable=True):
        # 入力を求める理由（「パスワードが違います」など）
        self.message = message
        self.user = user
        # URL でユーザー名が指定されている場合は変えられないようにする
        self.user_editable = user_editable


class RemoteLoginResult:
    """入力された内容"""

    def __init__(self, credentials, save):
        self.credentials = credentials
        # Windows の資格情報マネージャーに保存するかどうか
        self.save = save


class RemoteLoginWindow(viewkit.SubWindow):
    """ユーザー名とパスワードを入力するウィンドウ。parameters は RemoteLoginParameters。結果は RemoteLoginResult"""

    def __init__(self, parent, ctx, title, parameters: RemoteLoginParameters):
        super().__init__(parent, ctx, title, parameters)
        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        creator.staticText(parameters.message)
        self.user, dummy = creator.inputbox(
            _("ユーザー名"), default_value=parameters.user, x=300, style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
        self.user.hideScrollBar(wx.HORIZONTAL)
        if not parameters.user_editable:
            self.user.SetEditable(False)
        self.password, dummy = creator.inputbox(
            _("パスワード"), x=300, style=wx.BORDER_RAISED | wx.TE_DONTWRAP | wx.TE_PASSWORD)
        self.save = creator.checkbox(_("パスワードを保存する（Windows の資格情報マネージャーに保存します）"), state=False)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("接続"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))
        # ユーザー名が決まっている場合は、パスワードの入力から始める
        if parameters.user:
            self.password.SetFocus()
        else:
            self.user.SetFocus()

    def _on_ok(self, event):
        if self.user.GetLineText(0).strip() == "":
            simpleDialog.errorDialog(_("ユーザー名を入力してください。"), self)
            self.user.SetFocus()
            return
        event.Skip()

    def result(self):
        credentials = remote_storage.Credentials(self.user.GetLineText(0).strip(), self.password.GetValue())
        return RemoteLoginResult(credentials, self.save.GetValue())
