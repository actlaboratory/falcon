# -*- coding: utf-8 -*-
# Falcon openHere command Setting view
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import os

import viewkit.presets.keyValueSetting as keyValueSetting
import wx

import globalVars
import misc

from simpleDialog import dialog
from views.key_value_setting import EntryEditWindow, FalconKeyValueSettingWindow, validate_key_settings


def create_config(params: dict, keys: dict) -> keyValueSetting.KeyValueSettingConfig:
    """「ここで開く」の設定({名前:コマンド}, {名前:キー})から、設定ウィンドウに渡す設定を作る"""
    return keyValueSetting.KeyValueSettingConfig(
        listview_label=_("現在の登録内容"),
        keys=[
            keyValueSetting.KeyValueSettingKey("name", _("名前"), wx.LIST_FORMAT_LEFT, 200),
            keyValueSetting.KeyValueSettingKey("command", _("実行ファイル名"), wx.LIST_FORMAT_LEFT, 350),
            keyValueSetting.KeyValueSettingKey("key", _("ショートカット"), wx.LIST_FORMAT_LEFT, 200),
        ],
        values=[{"name": name, "command": command, "key": keys.get(name, "")} for name, command in params.items()],
        editor_window_class=OpenHereEditWindow,
        add_button_label=_("追加(&A)"),
        edit_button_label=_("変更(&M)"),
        delete_button_label=_("削除(&D)"),
    )


def split_rows(rows: list):
    """設定ウィンドウの結果から、({名前:コマンド}, {名前:キー})を作る"""
    return {row["name"]: row["command"] for row in rows}, {row["name"]: row["key"] for row in rows}


class OpenHereWindow(FalconKeyValueSettingWindow):
    """「ここで開く」コマンドの一覧を編集するウィンドウ。結果は一覧の行(辞書)のリスト。"""

    def __init__(self, parent, ctx, title, parameters):
        super().__init__(parent, ctx, title, parameters)
        self._old_keys = {row["name"]: row["key"] for row in parameters.values}

    def validate_rows(self, rows):
        """設定されたキーが重複している場合はエラーとする"""
        return validate_key_settings(self._old_keys, {row["name"]: row["key"] for row in rows}, self.log)


class OpenHereEditWindow(EntryEditWindow):
    """「ここで開く」コマンドの登録内容を入力するウィンドウ"""

    def __init__(self, parent, ctx, title, parameters):
        super().__init__(parent, ctx, title, parameters)
        self.add_field("name", _("名前"))
        self.add_field("command", _("実行ファイル名(引数指定可)"), button=(_("参照"), self._on_browse))
        self.add_field("key", _("ショートカット"), editable=False, button=(_("設定"), self._on_set_key))
        self.add_footer()

    def _on_browse(self, event):
        pathext = os.getenv("pathext").replace(";", ";*")
        d = wx.FileDialog(self, _("実行ファイルの選択"), wildcard=_("実行ファイル") + "(" + pathext + ")",
                          style=wx.FD_FILE_MUST_EXIST | wx.FD_SHOW_HIDDEN)
        if d.ShowModal() != wx.ID_CANCEL:
            self.fields["command"].SetValue(d.GetPath())
        d.Destroy()

    def _on_set_key(self, event):
        key = self.input_key("key")
        if key is None:
            self.fields["key"].SetValue("")
            globalVars.app.say(_("解除しました。"))
            return
        self.fields["key"].SetValue(key)
        globalVars.app.say(_("%s に設定しました。") % key)

    def validate(self):
        if self.get_value("command") == "":
            return False
        path, prm = misc.PathParamSplit(self.get_value("command"))
        if path is None:
            dialog(_("エラー"), _("指定された実行ファイルの書式が正しくありません。"), self)
            return False
        path = os.path.expandvars(path)
        if not os.path.isabs(path):
            dialog(_("エラー"), _("実行ファイルのパスは絶対パスで指定してください。"), self)
            return False
        if not os.path.isfile(path):
            dialog(_("エラー"), _("入力された実行ファイルが存在しません。パスを確認してください。"), self)
            return False
        if not misc.GetExecutableState(path):
            dialog(_("エラー"), _("指定されたファイルは存在しますが、実行可能な形式のファイルではありません。"), self)
            return False
        return True

    def result(self):
        row = super().result()
        row["name"] = row["name"].lower()  # 名前は大文字小文字を区別しない
        return row
