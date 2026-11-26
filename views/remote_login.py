# -*- coding: utf-8 -*-
# Falcon remote login view
# Note: All comments except these top lines will be written in Japanese.

"""FTP・SFTP のサーバーに接続するときのユーザー名とパスワード（SFTP では鍵ファイルも）を入力するウィンドウ"""

import os

import viewkit
import wx

import remote_storage
import simpleDialog


class RemoteLoginParameters:
    """RemoteLoginWindow に渡す値"""

    def __init__(self, message, user="", user_editable=True, insecure=False, use_key_file=False, key_file=""):
        # 入力を求める理由（「パスワードが違います」など）
        self.message = message
        self.user = user
        # URL でユーザー名が指定されている場合は変えられないようにする
        self.user_editable = user_editable
        # 暗号化しない接続（ftp://）で、パスワードがそのまま送られるかどうか
        self.insecure = insecure
        # SFTP の鍵ファイルを入力できるようにするかどうかと、その初期値
        self.use_key_file = use_key_file
        self.key_file = key_file


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
        message = parameters.message
        if parameters.insecure:
            message += "\n\n" + _(
                "注意: この接続（ftp://）は暗号化されません。パスワードや転送する内容が、そのままネットワークに流れます。\n"
                "サーバーが対応していれば、ftps://（FTPS）か sftp://（SFTP）で接続してください。")
        creator.staticText(message)
        self.user, dummy = creator.inputbox(
            _("ユーザー名"), default_value=parameters.user, x=300, style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
        self.user.hideScrollBar(wx.HORIZONTAL)
        if not parameters.user_editable:
            self.user.SetEditable(False)
        password_label = _("パスワード（鍵ファイルを使う場合はパスフレーズ）") if parameters.use_key_file else _("パスワード")
        self.password, dummy = creator.inputbox(
            password_label, x=300, style=wx.BORDER_RAISED | wx.TE_DONTWRAP | wx.TE_PASSWORD)
        self.key_file = None
        if parameters.use_key_file:
            key_creator = creator.makeChild(wx.HORIZONTAL, 0, "", wx.ALL | wx.EXPAND, margin=0)
            self.key_file, dummy = key_creator.inputbox(
                _("秘密鍵のファイル（使わない場合は空欄）"), default_value=parameters.key_file, x=300,
                style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
            self.key_file.hideScrollBar(wx.HORIZONTAL)
            key_creator.button(_("参照"), self._on_browse_key)
        self.save = creator.checkbox(_("パスワードを保存する（Windows の資格情報マネージャーに保存します）"), state=False)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("接続"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))
        # ユーザー名が決まっている場合は、パスワードの入力から始める
        if parameters.user:
            self.password.SetFocus()
        else:
            self.user.SetFocus()

    def _on_browse_key(self, event):
        default = os.path.expanduser("~\\.ssh")
        d = wx.FileDialog(self, _("秘密鍵のファイルを選択"), defaultDir=default if os.path.isdir(default) else "",
                          style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if d.ShowModal() != wx.ID_CANCEL:
            self.key_file.SetValue(d.GetPath())
        d.Destroy()
        self.key_file.SetFocus()

    def _get_key_file(self):
        if self.key_file is None:
            return ""
        return os.path.expandvars(self.key_file.GetLineText(0).strip().strip("\""))

    def _on_ok(self, event):
        if self.user.GetLineText(0).strip() == "":
            simpleDialog.errorDialog(_("ユーザー名を入力してください。"), self)
            self.user.SetFocus()
            return
        key_file = self._get_key_file()
        if key_file and not os.path.isfile(key_file):
            simpleDialog.errorDialog(_("鍵ファイルが見つかりません。"), self)
            self.key_file.SetFocus()
            return
        event.Skip()

    def result(self):
        password = self.password.GetValue()
        key_file = self._get_key_file()
        credentials = remote_storage.Credentials(
            self.user.GetLineText(0).strip(), password if password or not key_file else None, key_file)
        return RemoteLoginResult(credentials, self.save.GetValue())
