# -*- coding: utf-8 -*-
# Falcon remote permissions view
# Note: All comments except these top lines will be written in Japanese.

"""FTP・SFTP のサーバー上のファイル・フォルダのパーミッション（UNIX の rwx）を変更するウィンドウ"""

import re

import viewkit
import wx

import simpleDialog

# (表示名, ビット) の一覧。所有者・グループ・その他の順
_BITS = [
    (_("所有者: 読み取り"), 0o400), (_("所有者: 書き込み"), 0o200), (_("所有者: 実行"), 0o100),
    (_("グループ: 読み取り"), 0o040), (_("グループ: 書き込み"), 0o020), (_("グループ: 実行"), 0o010),
    (_("その他: 読み取り"), 0o004), (_("その他: 書き込み"), 0o002), (_("その他: 実行"), 0o001),
]


class RemotePermissionsParameters:
    """RemotePermissionsWindow に渡す値"""

    def __init__(self, target, mode):
        # 対象の表示名（「a.txt」「3項目」など）
        self.target = target
        # 今のパーミッション。わからない場合は None
        self.mode = mode


class RemotePermissionsWindow(viewkit.SubWindow):
    """パーミッションを変更するウィンドウ。parameters は RemotePermissionsParameters。結果は新しいパーミッション（数値）"""

    def __init__(self, parent, ctx, title, parameters: RemotePermissionsParameters):
        super().__init__(parent, ctx, title, parameters)
        self._result = None
        # 特殊なビット（setuid など）は、数値で入力したときだけ変える
        self._mode = parameters.mode if parameters.mode is not None else 0o644
        self._updating = False
        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        message = _("対象: %(target)s") % {"target": parameters.target}
        if parameters.mode is None:
            message += "\n" + _("現在のパーミッション: 不明")
        creator.staticText(message)
        self.checks = []
        for label, bit in _BITS:
            self.checks.append(creator.checkbox(label, self._on_check, state=bool(self._mode & bit)))
        self.number, dummy = creator.inputbox(
            _("数値（8進数）"), default_value="%03o" % (self._mode & 0o7777), x=100, style=wx.BORDER_RAISED | wx.TE_DONTWRAP)
        self.number.Bind(wx.EVT_TEXT, self._on_number)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))
        self.checks[0].SetFocus()

    def _on_check(self, event):
        """チェックボックスが変わったら、数値に反映する"""
        mode = self._mode & ~0o777
        for check, (dummy, bit) in zip(self.checks, _BITS):
            if check.GetValue():
                mode |= bit
        self._mode = mode
        self._updating = True
        self.number.SetValue("%03o" % mode)
        self._updating = False

    def _on_number(self, event):
        """数値が入力されたら、チェックボックスに反映する"""
        if self._updating:
            return
        mode = _parse(self.number.GetLineText(0))
        if mode is None:
            return
        self._mode = mode
        for check, (dummy, bit) in zip(self.checks, _BITS):
            check.SetValue(bool(mode & bit))

    def _on_ok(self, event):
        mode = _parse(self.number.GetLineText(0))
        if mode is None:
            simpleDialog.errorDialog(_("8進数 3～4桁で指定してください（例: 755）。"), self)
            self.number.SetFocus()
            return
        self._result = mode
        event.Skip()

    def result(self):
        return self._result


def _parse(text):
    """8進数の文字列をパーミッションにする。正しくなければ None"""
    text = text.strip()
    if not re.fullmatch(r"[0-7]{3,4}", text):
        return None
    return int(text, 8)
