# -*- coding: utf-8 -*-
# Falcon upload view
# Note: All comments except these top lines will be written in Japanese.

"""ファイル一覧で選んだ項目を FTP・SFTP のサーバーにアップロードするときの、アップロード先を入力するウィンドウ"""

import viewkit
import wx

import remote_storage
import remote_transfer
import simpleDialog


class UploadParameters:
    """UploadWindow に渡す値"""

    def __init__(self, candidates, default_value=""):
        # 候補の URL（開いているサーバーのタブ、ネットワークの場所など）
        self.candidates = candidates
        self.default_value = default_value


class UploadWindow(viewkit.SubWindow):
    """
    アップロード先のフォルダの URL と、同じ名前の項目があるときの扱いを入力するウィンドウ。
    parameters は UploadParameters。結果は (remote_storage.Location, remote_transfer.CONFLICT_*)。
    """

    def __init__(self, parent, ctx, title, parameters: UploadParameters):
        super().__init__(parent, ctx, title, parameters)
        self._result = None
        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        self.destination, dummy = creator.comboEdit(
            _("アップロード先のフォルダ（ftp://、ftps://、sftp:// の URL）"), parameters.candidates,
            default_value=parameters.default_value, x=500)
        self.conflict, dummy = creator.combobox(_("同じ名前の項目があるとき"), remote_transfer.get_conflict_names(), state=0)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

    def _on_ok(self, event):
        try:
            location = remote_storage.parse_url(self.destination.GetValue())
        except ValueError as err:
            simpleDialog.errorDialog(str(err), self)
            self.destination.SetFocus()
            return
        if location.path == "":
            simpleDialog.errorDialog(_("アップロード先のフォルダのパスを、サーバー名の後に / から入力してください。"), self)
            self.destination.SetFocus()
            return
        self._result = (location, remote_transfer.CONFLICTS[max(0, self.conflict.GetSelection())])
        event.Skip()

    def result(self):
        return self._result
