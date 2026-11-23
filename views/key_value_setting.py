# -*- coding: utf-8 -*-
# Falcon Key-Value setting view
# Copyright (C) 2020-2021 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
viewkit の KeyValueSettingWindow(一覧の追加・変更・削除を行うウィンドウ)に、falcon で必要な以下の機能を追加したもの。
- ボタンの表示名の日本語化
- 一覧の先頭の項目(登録名など)が重複したときの上書き確認
- 削除できない行の指定
- OK ボタンを押したときの一覧全体の検証
また、一覧の各行を編集するウィンドウの基底クラスと、ショートカットキーの設定内容の検証も提供する。
"""

from logging import getLogger

import viewkit
import viewkit.presets.keyValueSetting as keyValueSetting
import wx

import constants
import globalVars
import keymap

from simpleDialog import dialog

# 一覧に表示する、ショートカットキーが無いことを表す文字列
NO_KEY = _("なし")


class FalconKeyValueSettingWindow(keyValueSetting.KeyValueSettingWindow):
    def __init__(self, parent, ctx, title, parameters: keyValueSetting.KeyValueSettingConfig):
        super().__init__(parent, ctx, title, parameters)
        self.log = getLogger("%s.%s" % (constants.LOG_PREFIX, self.__class__.__name__))
        self._key_name = self.config.keys[0].key
        # viewkit のボタンの表示名を日本語にし、OKボタンでは一覧全体を検証する
        ok_button = self.FindWindowById(wx.ID_OK, self)
        ok_button.SetLabel(_("ＯＫ"))
        ok_button.Bind(wx.EVT_BUTTON, self._on_ok)
        self.FindWindowById(wx.ID_CANCEL, self).SetLabel(_("キャンセル"))

    def can_delete(self, row: dict) -> bool:
        """指定された行を削除できるかを返す。制限したい場合はオーバーライドする。"""
        return True

    def validate_rows(self, rows: list) -> bool:
        """OKボタンが押されたときに、一覧全体を検証する。問題があればFalseを返す。必要に応じてオーバーライドする。"""
        return True

    def _on_ok(self, event):
        if self.validate_rows(self._value_rows):
            event.Skip()

    def _handleAdd(self, event):
        count = len(self._value_rows)
        super()._handleAdd(event)
        if len(self._value_rows) > count:
            self._resolve_duplicate(len(self._value_rows) - 1)
        self.Raise()

    def _handleEdit(self, event):
        index = self._lst.GetFirstSelected()
        original = self._value_rows[index] if index >= 0 else None
        super()._handleEdit(event)
        if index >= 0 and self._value_rows[index] is not original:
            self._resolve_duplicate(index)
        self.Raise()

    def _handleDelete(self, event):
        index = self._lst.GetFirstSelected()
        if index < 0 or not self.can_delete(self._value_rows[index]):
            return
        super()._handleDelete(event)

    def _resolve_duplicate(self, index):
        """追加・変更された行の先頭の項目が既存の行と重複していれば、上書きするかを確認する"""
        key = self._value_rows[index].get(self._key_name, "")
        duplicate = [i for i, row in enumerate(self._value_rows) if i != index and row.get(self._key_name, "").lower() == key.lower()]
        if not duplicate:
            return
        dlg = wx.MessageDialog(self, _("この%sは既に登録されています。登録を上書きしますか？") % self.config.keys[0].display_name,
                               _("上書き確認"), wx.YES_NO | wx.ICON_QUESTION)
        overwrite = dlg.ShowModal() == wx.ID_YES
        dlg.Destroy()
        # 上書きするなら既存の行を、しないなら今回の行を削除する
        targets = duplicate if overwrite else [index]
        for i in sorted(targets, reverse=True):
            self._lst.DeleteItem(i)
            del self._value_rows[i]
        self._lst.SetFocus()


class EntryEditWindow(viewkit.SubWindow):
    """一覧の1行分の内容を入力するウィンドウの基底クラス。parametersは viewkit の KeyValueSettingEditEvent。"""

    def __init__(self, parent, ctx, title, parameters: keyValueSetting.KeyValueSettingEditEvent):
        super().__init__(parent, ctx, title, parameters)
        # viewkit からは英語のタイトルで呼ばれるので置き換える
        self.SetTitle(_("登録内容の入力"))
        self.row = dict(parameters.original_value_row) if parameters.original_value_row else {}
        self.fields = {}
        self._fields_creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL, margin=20)

    def add_field(self, key: str, label: str, editable=True, button=None, hidden=False):
        """
        入力欄を追加する。
        button には (表示名, イベントハンドラ) を指定するとボタンを横に設置する。hidden=True なら値の保持のみに使う。
        """
        creator = self._fields_creator.makeChild(wx.HORIZONTAL, 10)
        style = 0 if editable else wx.TE_READONLY
        edit, dummy = creator.inputbox(label, x=500, default_value=str(self.row.get(key, "")), style=style, text_layout=wx.VERTICAL)
        edit.hideScrollBar(wx.HORIZONTAL)
        if hidden:
            edit.GetParent().Hide()
        if button:
            creator.button(button[0], button[1], sizer_flag=wx.ALIGN_BOTTOM | wx.BOTTOM, margin=10)
        self.fields[key] = edit
        return edit

    def add_footer(self):
        """OK・キャンセルボタンを設置する。add_fieldの後に呼ぶ。"""
        footer = self.creator.makeChild(wx.HORIZONTAL, 20, "", wx.ALIGN_RIGHT | wx.TOP, 10)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

    def get_value(self, key: str) -> str:
        return self.fields[key].GetLineText(0)

    def validate(self) -> bool:
        """OKボタンが押されたときの入力値の検証。問題があればFalseを返す。必要に応じてオーバーライドする。"""
        return True

    def _on_ok(self, event):
        first_key = next(iter(self.fields))
        value = self.get_value(first_key)
        if value == "" or "=" in value:
            dialog(_("エラー"), _("%sを空白や半角の=を含む値に設定することはできません。") % self.fields[first_key].GetName(), self)
            return
        if self.validate():
            event.Skip()

    def result(self):
        return {key: edit.GetLineText(0) for key, edit in self.fields.items()}

    def input_key(self, key: str, key_filter=None):
        """ショートカットキーの入力ウィンドウを表示し、結果を入力欄に反映する"""
        import views.keyConfig
        ret = self.showSubWindow(views.keyConfig.KeyInputWindow, _("キー設定"), key_filter)
        return ret.user_object if ret.code == wx.ID_OK else None


def validate_key_settings(old_key_config: dict, new_key_config: dict, logger=None, entries=None, allow_new_key_duplication=False) -> bool:
    """
    ショートカットキーの設定内容を検証し、問題があればエラーを表示してFalseを返す。

    old_key_config:	{name:key}	設定変更前
    new_key_config:	{name:key}	設定変更後
    logger:			エラー時のログ出力用
    entries:		重複判定対象のAcceleratorEntryのリスト(省略時はメインウィンドウのもの)
    allow_new_key_duplication:	new_key_config内での重複を許すならTrue
    """
    if logger is None:
        logger = getLogger("%s.%s" % (constants.LOG_PREFIX, "KeySettingValidation"))
    errors = ""
    old_keys = {}
    for k, vs in old_key_config.items():
        for v in vs.split("/"):
            old_keys.setdefault(v, list()).append(k)
    new_keys = {}
    for k, vs in new_key_config.items():
        for v in vs.split("/"):
            new_keys.setdefault(v, list()).append(k)
    if entries is None:
        entries = globalVars.app.main_window.get_key_entries()

    for k, v in new_keys.items():
        if k == NO_KEY or k == "":
            continue
        if not allow_new_key_duplication:
            if len(v) == 2:
                errors += _("%(v1)sと%(v2)sに同じショートカットキー%(key)sが設定されています。\n") % {"v1": v[0], "v2": v[1], "key": k}
                continue
            elif len(v) > 2:
                errors += _("%(v1)s、%(v2)sなど計%(count)d箇所に同じショートカットキー%(key)sが設定されています。\n") % {"v1": v[0], "v2": v[1], "count": len(v), "key": k}
                continue
        e = keymap.make_entry("DUMMY", k, None, logger)
        if e is None:
            errors += _("設定されたショートカット%sが認識できません。お手数ですが、このエラーメッセージを作者へご連絡ください。\n") % k
        elif e in entries and (k not in old_keys):
            errors += _("%(command)sに設定されたショートカットキー%(key)sは、別の場所で利用されています。\n") % {"command": v[0], "key": k}
    if errors != "":
        dialog(_("エラー"), errors)
        return False
    return True
