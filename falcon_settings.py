# -*- coding: utf-8 -*-
# Falcon settings
# Copyright (C) 2019 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
falcon固有の設定を、viewkitの設定ファイル(JSON)に保存・読み込みするためのモジュール。

viewkitが管理する設定(ウィンドウ位置・フォント・表示モード・ショートカットキー)以外は、
JSONの custom.falcon 以下に「セクション -> キー -> 値」の形で保存する。
キー名はiniファイルとの互換性のため、常に小文字で扱う。
"""

import configparser
import os

from logging import getLogger

import viewkit

# 設定ファイル名
SETTING_FILE_NAME = "settings.json"
OLD_SETTING_FILE_NAME = "settings.ini"
OLD_KEYMAP_FILE_NAME = "keymap.ini"

# viewkit の custom 以下に登録するフィールド名
CUSTOM_FIELD_NAME = "falcon"

# キーの削除が許されない設定のデフォルト値。
# ユーザ側の設定に値がなければここでの値がそのまま利用される。
DEFAULT_VALUES = {
    "general": {
        "confirm_unrecyclable": True,
        "language": "ja-JP",
        "fileversion": "100",
        "locale": "ja-JP",
        "log_level": "0",
        "update": True,
    },
    "speech": {
        "reader": "AUTO",
        "fx_volume": 100,
    },
    "proxy": {
        "usemanualsetting": False,
        "server": "localhost",
        "port": 8080,
    },
    "FileList": {
        "sorting": 0,
        "descending": 0,
        "column_width_0": 650,
        "column_width_1": 150,
        "column_width_2": 320,
        "column_width_3": 70,
        "column_width_4": 240,
    },
    "GrepResultList": {
        "sorting": 0,
        "descending": 0,
        "column_width_0": 300,
        "column_width_1": 80,
        "column_width_2": 300,
        "column_width_3": 70,
        "column_width_4": 150,
        "column_width_5": 320,
        "column_width_6": 70,
        "column_width_7": 240,
    },
    "DriveList": {
        "sorting": 1,
        "descending": 0,
        "column_width_0": 250,
        "column_width_1": 120,
        "column_width_2": 150,
        "column_width_3": 150,
        "column_width_4": 480,
    },
    "SearchResultList": {
        "sorting": 0,
        "descending": 0,
        "column_width_0": 330,
        "column_width_1": 150,
        "column_width_2": 320,
        "column_width_3": 320,
        "column_width_4": 70,
        "column_width_5": 240,
    },
    "NetworkResourceList": {
        "sorting": 0,
        "descending": 0,
        "column_width_0": 620,
    },
    "RemoteList": {
        "sorting": 0,
        "descending": 0,
        "column_width_0": 500,
        "column_width_1": 110,
        "column_width_2": 200,
        "column_width_3": 230,
    },
    "view": {
        "header_title_length": 20,
        "hide_extension": False,
    },
    "browse": {
        "startpath": "",
    },
    "search": {
        "history_count": 20,
    },
    "sounds": {
        "startup": "tip.ogg",
        "boundary": "tip.ogg",
        "checked": "click.ogg",
        "check": "checked.ogg",
    },
    "preview": {
        "header_line_count": 10,
        "footer_line_count": 10,
        "audio_volume": 100,
    },
    "on_list_moved": {
        "read_directory_level": True,
        "read_directory_name": True,
        "read_item_count": True,
    },
}

# ユーザによるキーの削除が許されるが、初回起動時に組み込んでおきたい設定の初期値。
# ユーザの環境に設定ファイルがなかった場合のみ適用される。
INITIAL_VALUES = {
    "favorite_directories": {
        "ドキュメント": r"%userprofile%\documents",
        "デスクトップ": r"%userprofile%\desktop",
    },
    "favorite_directories_shortcut": {
        "ドキュメント": "alt+1",
        "デスクトップ": "alt+2",
    },
    "open_here": {
        "Explorer": "%windir%\\explorer.exe \"%1\"",
        "コマンド プロンプト": "%windir%\\system32\\cmd.exe /K cd /d  \"%1\"",
        "Windows Power Shell": "%windir%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe -NoExit -command cd '%1'",
    },
    "open_here_shortcut": {
        "Explorer": "ctrl+e",
        "コマンド プロンプト": "ctrl+shift+o",
        "Windows Power Shell": "ctrl+shift+p",
    },
    "originalAssociation": {
        "<default_file>": r"C:\Program Files (x86)\KSD\MyEdit\MyEdit.exe",
        "<default_dir>": "falcon.exe",
    },
}

# viewkit の設定として保存する表示関係の初期値
DEFAULT_FONT = "bold 'ＭＳ ゴシック' 22 windows-932"

_TRUE_STRINGS = ("1", "yes", "true", "on")
_FALSE_STRINGS = ("0", "no", "false", "off")


def get_custom_setting_fields():
    """ApplicationContext に登録する、falcon用のカスタム設定フィールドを返す"""
    # スキーマを空にして、中身の検証はこのモジュールで行う
    return [viewkit.CustomSettingField(CUSTOM_FIELD_NAME, {})]


def _normalize_key(section, key):
    """iniと同様、キー名は小文字で扱う。お気に入りなどユーザが名前を付けるセクションは除く"""
    if section in _CASE_SENSITIVE_SECTIONS:
        return key
    return key.lower()


# キーがユーザ指定の名前であるため、大文字小文字を区別するセクション
_CASE_SENSITIVE_SECTIONS = (
    "favorite_directories",
    "favorite_directories_shortcut",
    "open_here",
    "open_here_shortcut",
    "remote_places",
)


class FalconSettings:
    """viewkit の SettingsManager 上に falcon固有の設定を保存するためのクラス"""

    def __init__(self, settings_manager):
        self._settings = settings_manager
        self._log = getLogger("falcon.settings")
        data = self._settings.getSetting("custom.%s" % CUSTOM_FIELD_NAME, None)
        if not isinstance(data, dict) or not data:
            # 初回起動
            self._log.info("falcon settings not found. initial values will be applied.")
            data = {}
            for section, values in INITIAL_VALUES.items():
                data[section] = dict(values)
        self._data = data
        # デフォルト値を補完
        for section, values in DEFAULT_VALUES.items():
            target = self._data.setdefault(section, {})
            for key, value in values.items():
                target.setdefault(key, value)
        self._store()

    def _store(self):
        self._settings.setCustomSetting(CUSTOM_FIELD_NAME, self._data)

    def save(self):
        """設定をファイルに保存する"""
        self._store()
        self._settings.save()

    def has_section(self, section: str) -> bool:
        return section in self._data

    def get_section(self, section: str) -> dict:
        """セクション内の設定を辞書のコピーで返す。セクションがなければ空の辞書を返す"""
        return dict(self._data.get(section, {}))

    def replace_section(self, section: str, values: dict):
        """セクションの内容を丸ごと置き換える"""
        self._data[section] = {_normalize_key(section, k): v for k, v in values.items()}
        self._store()

    def remove_section(self, section: str):
        self._data.pop(section, None)
        self._store()

    def get(self, section: str, key: str, default=""):
        """設定値をそのまま返す。値がなければ default を保存して返す"""
        key = _normalize_key(section, key)
        values = self._data.setdefault(section, {})
        if key not in values:
            values[key] = default
            self._store()
        return values[key]

    def set(self, section: str, key: str, value):
        """設定値を変更する"""
        self._data.setdefault(section, {})[_normalize_key(section, key)] = value
        self._store()

    def get_str(self, section: str, key: str, default: str = "", selection=None) -> str:
        """文字列として値を返す。空文字列や selection 外の値の場合は default を保存して返す"""
        if selection is not None and not hasattr(selection, "__iter__"):
            raise TypeError("selection must be iterable. %s were given." % type(selection))
        value = self.get(section, key, default)
        value = "" if value is None else str(value)
        if value == "" and default != "":
            self._log.debug("add default value. at section %s, key %s" % (section, key))
            self.set(section, key, default)
            value = default
        if selection is not None and value not in selection:
            self._log.debug("value %s not in selection. at section %s, key %s" % (value, section, key))
            self.set(section, key, default)
            value = default
        return value

    def get_int(self, section: str, key: str, default: int = 0, min: int = None, max: int = None) -> int:
        """整数として値を返す。整数でない場合や範囲外の場合は default を保存して返す"""
        if type(default) != int:
            raise ValueError("default value must be int")
        if (min is not None and type(min) != int) or (max is not None and type(max) != int):
            raise ValueError("min/max value must be int")
        value = self.get(section, key, default)
        try:
            if isinstance(value, bool):
                raise ValueError
            value = int(value)
        except (TypeError, ValueError):
            self._log.debug("value is not int. return default %d at section %s, key %s" % (default, section, key))
            self.set(section, key, default)
            return default
        if (min is not None and value < min) or (max is not None and value > max):
            self._log.debug("int value %d out of range. at section %s, key %s" % (value, section, key))
            self.set(section, key, default)
            return default
        return value

    def get_bool(self, section: str, key: str, default: bool = True) -> bool:
        """真偽値として値を返す。真偽値として解釈できない場合は default を保存して返す"""
        if type(default) != bool:
            raise ValueError("default value must be boolean")
        value = self.get(section, key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            if value.lower() in _TRUE_STRINGS:
                return True
            if value.lower() in _FALSE_STRINGS:
                return False
        self._log.debug("value is not boolean. return default %s at section %s, key %s" % (default, section, key))
        self.set(section, key, default)
        return default


def migrate_from_ini(json_file_name: str = SETTING_FILE_NAME, ini_file_name: str = OLD_SETTING_FILE_NAME,
                     keymap_file_name: str = OLD_KEYMAP_FILE_NAME) -> bool:
    """
    旧バージョンの settings.ini / keymap.ini から、viewkit形式の設定ファイル(JSON)を作成する。
    JSONが既に存在する場合や、iniが存在しない場合は何もしない。
    移行を実施した場合は True を返す。
    """
    log = getLogger("falcon.settings")
    if os.path.exists(json_file_name):
        return False
    if not os.path.exists(ini_file_name) and not os.path.exists(keymap_file_name):
        return False
    log.info("migrating settings from %s and %s" % (ini_file_name, keymap_file_name))

    ini = _read_ini(ini_file_name)
    falcon_data = {}
    for section in ini.sections():
        falcon_data[section] = {}
        for key, value in ini.items(section):
            falcon_data[section][_normalize_key(section, key)] = value

    data = {"custom": {CUSTOM_FIELD_NAME: falcon_data}}

    # viewkit が管理する設定へ移す
    view_section = falcon_data.get("view", {})
    data["view"] = {
        "is_dark": view_section.pop("colormode", "white").lower() == "dark",
        "is_word_wrap": view_section.pop("textwrapping", "off").lower() == "on",
        "font": view_section.pop("font", DEFAULT_FONT),
    }
    main_view = falcon_data.pop("mainView", {})
    main_window = {}
    for old, new in (("positionx", "x"), ("positiony", "y"), ("sizex", "size_x"), ("sizey", "size_y")):
        try:
            main_window[new] = max(int(main_view[old]), 0 if new in ("x", "y") else -1)
        except (KeyError, ValueError):
            pass
    if main_view.get("maximized", "False").lower() in _TRUE_STRINGS:
        main_window["maximized"] = 1
    data["main_window"] = main_window

    # ショートカットキー
    keymap = _read_ini(keymap_file_name)
    if keymap.has_section("MAINVIEW"):
        data["shortcuts"] = {key.upper(): value for key, value in keymap.items("MAINVIEW")}

    # viewkit の SettingsManager で検証・正規化して保存する
    manager = viewkit.settings.SettingsManager(json_file_name)
    for field in get_custom_setting_fields():
        manager.registerCustomField(field)
    manager.loadOrCreateDefault()
    for key in ("view", "main_window"):
        for sub_key, value in data[key].items():
            manager.changeSetting("%s.%s" % (key, sub_key), value)
    if "shortcuts" in data:
        manager.changeSetting("shortcuts", data["shortcuts"])
    manager.setCustomSetting(CUSTOM_FIELD_NAME, falcon_data)
    manager.save()
    log.info("settings migrated to %s" % json_file_name)
    return True


def _read_ini(file_name):
    parser = configparser.ConfigParser(interpolation=None)
    if os.path.exists(file_name):
        try:
            parser.read(file_name, encoding="UTF-8")
        except configparser.Error:
            getLogger("falcon.settings").warning("failed to parse %s" % file_name)
    return parser
