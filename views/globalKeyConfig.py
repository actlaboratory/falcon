# -*- coding: utf-8 -*-
# Falcon globalKeyConfig view
# Copyright (C) 2021 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

from logging import getLogger

import viewkit.presets.keyValueSetting as keyValueSetting
import wx

import constants
import globalVars
import keymap

from simpleDialog import dialog, errorDialog
from views.key_value_setting import NO_KEY, EntryEditWindow, FalconKeyValueSettingWindow, validate_key_settings

# 1つの機能に設定できるショートカットキーの数
MAX_KEY_COUNT = 5


class GlobalKeyConfigParameters(keyValueSetting.KeyValueSettingConfig):
    """GlobalKeyConfigWindow に渡すパラメータ"""

    def __init__(self, rows: list, check_entries=None, key_filter=None):
        """rowsには {"name": 表示名, "key": キー("/"区切り、無ければNO_KEY), "identifier": 機能の識別子} のリストを指定する"""
        super().__init__(
            listview_label=_("現在の登録内容"),
            keys=[
                keyValueSetting.KeyValueSettingKey("name", _("名前"), wx.LIST_FORMAT_LEFT, 350),
                keyValueSetting.KeyValueSettingKey("key", _("ショートカット"), wx.LIST_FORMAT_LEFT, 370),
                keyValueSetting.KeyValueSettingKey("identifier", _("識別子"), wx.LIST_FORMAT_LEFT, 200),
            ],
            values=rows,
            allow_edit_rows=False,
            editor_window_class=KeyEditWindow,
            add_button_label=_("追加(&A)"),
            edit_button_label=_("変更(&M)"),
            delete_button_label=_("削除(&D)"),
        )
        self.check_entries = check_entries if check_entries is not None else []
        self.key_filter = key_filter if key_filter is not None else globalVars.app.main_window.menu.keymap.key_filter


class GlobalKeyConfigWindow(FalconKeyValueSettingWindow):
    """ショートカットキーの一覧を編集するウィンドウ。結果は一覧の行(辞書)のリスト。"""

    def __init__(self, parent, ctx, title, parameters: GlobalKeyConfigParameters):
        super().__init__(parent, ctx, title, parameters)
        self._old_keys = {row["name"]: row["key"] for row in parameters.values}
        # 行の追加・削除はできない
        for label in (parameters.add_button_label, parameters.delete_button_label):
            button = self.FindWindowByLabel(label, self)
            if button is not None:
                button.Hide()

    def validate_rows(self, rows):
        """設定されたキーが重複している場合はエラーとする"""
        names = {row["name"]: row["key"] for row in rows}
        # 他のビューとの重複調査
        if not validate_key_settings(self._old_keys, names, self.log, self.config.check_entries, True):
            return False

        # このビュー内での重複調査
        identifiers = {row["name"]: row["identifier"] for row in rows}
        new_keys = {}
        for name, keys in names.items():
            for key in keys.split("/"):
                new_keys.setdefault(key.upper(), set()).add(name)
        for key, key_names in new_keys.items():
            if key == NO_KEY:
                continue
            if len(key_names) >= 2:
                entries = [keymap.make_entry(identifiers[name], key, None, self.log) for name in key_names]
                if not keymap.permit_conflict(entries, self.log):
                    dialog(_("エラー"), _("以下の項目において、重複するキー %(key)s が設定されています。\n\n%(command)s") % {"key": key, "command": key_names}, self)
                    return False
        return True


class KeyEditWindow(EntryEditWindow):
    """1つの機能のショートカットキーを設定するウィンドウ"""

    def __init__(self, parent, ctx, title, parameters):
        super().__init__(parent, ctx, title, parameters)
        self.log = getLogger("%s.%s" % (constants.LOG_PREFIX, self.__class__.__name__))
        self.key_filter = globalVars.app.main_window.menu.keymap.key_filter
        keys = self.row.get("key", NO_KEY).split("/")
        keys += [NO_KEY] * (MAX_KEY_COUNT - len(keys))
        self.add_field("name", _("名前"), editable=False)
        for i in range(MAX_KEY_COUNT):
            self.row["key%d" % i] = keys[i]
            self.add_field("key%d" % i, _("ショートカット%d") % (i + 1), editable=False,
                           button=(_("設定"), lambda event, no=i: self._on_set_key(no)))
        self.add_field("identifier", _("識別子"), editable=False, hidden=True)
        self.add_footer()

    def _on_set_key(self, no):
        field = self.fields["key%d" % no]
        # フィルタに引っかかるものが既に設定されている場合、その変更は許さない
        before = field.GetLineText(0)
        if before != NO_KEY and not self.key_filter.check(before):
            errorDialog(_("このショートカットは変更できません。"), self)
            return
        key = self.input_key("key%d" % no, self.key_filter)
        if key is None:
            dialog(_("設定完了"), _("解除しました。"), self)
            field.SetValue(NO_KEY)
        else:
            dialog(_("設定完了"), _("%s に設定しました。") % key, self)
            field.SetValue(key)

    def validate(self):
        # 同一パターンを２重指定している場合は、後のものを解除する
        entries = []
        for i in range(MAX_KEY_COUNT):
            field = self.fields["key%d" % i]
            if field.GetLineText(0) != NO_KEY:
                entry = keymap.make_entry(self.get_value("name"), field.GetLineText(0), None, self.log)
                if entry in entries:
                    field.SetValue(NO_KEY)
                else:
                    entries.append(entry)
        return True

    def result(self):
        keys = [self.get_value("key%d" % i) for i in range(MAX_KEY_COUNT)]
        keys = [key for key in keys if key != NO_KEY]
        return {
            "name": self.get_value("name"),
            "key": "/".join(keys) if keys else NO_KEY,
            "identifier": self.get_value("identifier"),
        }
