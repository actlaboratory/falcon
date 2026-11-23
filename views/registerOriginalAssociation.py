# -*- coding: utf-8 -*-
# Falcon register originalAssociation view
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import os
import re

import viewkit.presets.keyValueSetting as keyValueSetting
import wx

import misc

from simpleDialog import dialog
from views.key_value_setting import EntryEditWindow, FalconKeyValueSettingWindow

# 拡張子ではなく、既定の関連付けを表す名前の接頭辞
DEFAULT_PREFIX = "<default_"


def create_config(associations: dict) -> keyValueSetting.KeyValueSettingConfig:
    """独自関連付けの設定({拡張子:実行ファイル})から、設定ウィンドウに渡す設定を作る"""
    return keyValueSetting.KeyValueSettingConfig(
        listview_label=_("現在の登録内容"),
        keys=[
            keyValueSetting.KeyValueSettingKey("extention", _("拡張子"), wx.LIST_FORMAT_LEFT, 250),
            keyValueSetting.KeyValueSettingKey("path", _("実行ファイル名"), wx.LIST_FORMAT_LEFT, 550),
        ],
        values=[{"extention": extention, "path": path} for extention, path in associations.items()],
        editor_window_class=OriginalAssociationEditWindow,
        add_button_label=_("追加(&A)"),
        edit_button_label=_("変更(&M)"),
        delete_button_label=_("削除(&D)"),
    )


def rows_to_dict(rows: list) -> dict:
    """設定ウィンドウの結果から、{拡張子:実行ファイル}を作る"""
    return {row["extention"]: row["path"] for row in rows}


class OriginalAssociationWindow(FalconKeyValueSettingWindow):
    """拡張子の独自関連付けの一覧を編集するウィンドウ。結果は一覧の行(辞書)のリスト。"""

    def can_delete(self, row):
        # 既定の関連付けは削除できない
        return DEFAULT_PREFIX not in row["extention"]


class OriginalAssociationEditWindow(EntryEditWindow):
    """拡張子と実行ファイルの関連付けを入力するウィンドウ"""

    def __init__(self, parent, ctx, title, parameters):
        super().__init__(parent, ctx, title, parameters)
        is_default = DEFAULT_PREFIX in self.row.get("extention", "")
        self.add_field("extention", _("拡張子"), editable=not is_default)
        self.add_field("path", _("実行ファイル名"), button=(_("参照"), self._on_browse))
        self.add_footer()

    def _on_browse(self, event):
        pathext = os.getenv("pathext").replace(";", ";*")
        d = wx.FileDialog(self, _("実行ファイルの選択"), wildcard=_("実行ファイル") + "(" + pathext + ")",
                          style=wx.FD_FILE_MUST_EXIST | wx.FD_SHOW_HIDDEN)
        if d.ShowModal() != wx.ID_CANCEL:
            self.fields["path"].SetValue(d.GetPath())
        d.Destroy()

    def validate(self):
        if self.get_value("path") == "":
            return False
        path = os.path.expandvars(self.get_value("path"))
        if not os.path.isabs(path):
            dialog(_("エラー"), _("実行ファイルのパスは絶対パスで指定してください。"), self)
            return False
        if not os.path.isfile(path):
            dialog(_("エラー"), _("入力された実行ファイルが存在しません。パスを確認してください。"), self)
            return False
        if not misc.GetExecutableState(path):
            dialog(_("エラー"), _("指定されたファイルは存在しますが、実行可能な形式のファイルではありません。"), self)
            return False
        extention = self.get_value("extention")
        if extention in ("<default_file>", "<default_dir>"):
            return True
        if not re.match("^[a-zA-Z0-9\\-$~]+$", extention):
            dialog(_("エラー"), _("入力された拡張子に利用できない文字が含まれています。"), self)
            return False
        return True

    def result(self):
        row = super().result()
        row["extention"] = row["extention"].lower()
        return row
