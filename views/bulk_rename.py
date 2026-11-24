# -*- coding: utf-8 -*-
# Falcon bulk rename view
# Note: All comments except these top lines will be written in Japanese.

"""正規表現で名前を一括置換するウィンドウ"""

import re

import viewkit
import wx

import bulk_rename

from simpleDialog import dialog

# 入力が止まってから一覧を作り直すまでの時間(ミリ秒)
_PREVIEW_DELAY = 300
# エラーの一覧を表示するときの最大行数
_MAX_ERROR_LINES = 10


class BulkRenameWindow(viewkit.SubWindow):
    """
    検索する正規表現と置換文字列を入力し、変更後の名前を確認して一括置換するウィンドウ。
    parameters は bulk_rename.RenameTarget のリスト。
    結果は、名前を変更する項目の bulk_rename.RenamePlan のリスト。
    """

    def __init__(self, parent, ctx, title, parameters: list):
        super().__init__(parent, ctx, title, parameters)
        self._plans = []
        self._timer = None

        creator = self.creator.makeChild(wx.VERTICAL, 20, "", wx.EXPAND)
        self.pattern, dummy = creator.inputbox(_("検索する正規表現"), self._on_changed, x=500)
        self.replacement, dummy = creator.inputbox(_("置換後の文字列"), self._on_changed, x=500)
        self.ignore_case = creator.checkbox(_("大文字と小文字を区別しない"), self._on_changed, False)
        self.include_extension = creator.checkbox(_("拡張子も置換の対象にする"), self._on_changed, False)

        self.summary = creator.staticText("", x=600)
        self.list_ctrl, dummy = creator.listCtrl(
            _("変更後の名前"), proportion=0, sizer_flag=wx.ALL | wx.EXPAND, size=(600, 300),
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list_ctrl.InsertColumn(0, _("今の名前"), width=200)
        self.list_ctrl.InsertColumn(1, _("新しい名前"), width=200)
        self.list_ctrl.InsertColumn(2, _("状態"), width=200)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, "", wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

        self._update_preview()

    def result(self):
        return [p for p in self._plans if p.status == bulk_rename.STATUS_OK]

    def _on_changed(self, event):
        """入力が変わったら、少し待ってから一覧を作り直す"""
        if self._timer is not None and self._timer.IsRunning():
            self._timer.Stop()
        self._timer = wx.CallLater(_PREVIEW_DELAY, self._update_preview)

    def _make_plans(self):
        """入力内容から置換結果を作る。パターンが空なら空のリスト。文法が間違っていれば re.error。"""
        pattern = self.pattern.GetValue()
        if pattern == "":
            return []
        return bulk_rename.make_plans(
            self.parameters, pattern, self.replacement.GetValue(),
            self.ignore_case.IsChecked(), self.include_extension.IsChecked())

    def _update_preview(self):
        """変更後の名前の一覧を作り直す"""
        if not self:
            return  # ウィンドウが閉じた後に呼ばれた
        try:
            self._plans = self._make_plans()
        except re.error as e:
            self._plans = []
            self.summary.SetLabel(_("正規表現の文法が間違っています: %(error)s") % {"error": e})
            self._show_targets()
            return
        if not self._plans:
            self.summary.SetLabel(_("対象 %(count)d件。検索する正規表現を入力してください。") % {"count": len(self.parameters)})
            self._show_targets()
            return
        self.summary.SetLabel(_("変更 %(ok)d件、変更なし %(unchanged)d件、エラー %(error)d件") % {
            "ok": bulk_rename.count_status(self._plans, bulk_rename.STATUS_OK),
            "unchanged": bulk_rename.count_status(self._plans, bulk_rename.STATUS_UNCHANGED),
            "error": bulk_rename.count_status(self._plans, bulk_rename.STATUS_ERROR),
        })
        self.list_ctrl.DeleteAllItems()
        for plan in self._plans:
            status = _("変更") if plan.status == bulk_rename.STATUS_OK else plan.message
            self.list_ctrl.Append((plan.target.basename, plan.new_name, status))

    def _show_targets(self):
        """置換結果がないときは、対象の名前だけを並べる"""
        self.list_ctrl.DeleteAllItems()
        for target in self.parameters:
            self.list_ctrl.Append((target.basename, "", ""))

    def _on_ok(self, event):
        """入力内容を検証し、問題がなければ閉じる"""
        if self._timer is not None and self._timer.IsRunning():
            self._timer.Stop()
        if self.pattern.GetValue() == "":
            dialog(_("エラー"), _("検索する正規表現を入力してください。"), self)
            return
        try:
            self._plans = self._make_plans()
        except re.error as e:
            dialog(_("エラー"), _("正規表現の文法が間違っています。\nエラー内容: %(error)s") % {"error": e}, self)
            return
        self._update_preview()
        errors = [p for p in self._plans if p.status == bulk_rename.STATUS_ERROR]
        if errors:
            lines = ["%s: %s" % (p.target.basename, p.message) for p in errors[:_MAX_ERROR_LINES]]
            if len(errors) > _MAX_ERROR_LINES:
                lines.append(_("ほか %(count)d件") % {"count": len(errors) - _MAX_ERROR_LINES})
            dialog(_("エラー"), _("名前を変更できない項目が %(count)d件あります。\n\n%(lines)s") % {
                "count": len(errors), "lines": "\n".join(lines)}, self)
            return
        if bulk_rename.count_status(self._plans, bulk_rename.STATUS_OK) == 0:
            dialog(_("エラー"), _("名前が変わる項目がありません。"), self)
            return
        event.Skip()
