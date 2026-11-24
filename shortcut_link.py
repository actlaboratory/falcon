# -*- coding: utf-8 -*-
# Falcon shortcut (.lnk) information
# Note: All comments except these top lines will be written in Japanese.

"""
ショートカット（.lnk）の設定の読み書き。
エクスプローラーのプロパティの「ショートカット」タブにある項目を扱う。
読み書きには IShellLink と IShellLinkDataList を使う。
"""

import os

import pythoncom
import win32con
from win32com import storagecon
from win32com.shell import shell, shellcon

# 実行時の大きさ。エクスプローラーと同じく、最小化は「アクティブにしない最小化」を使う
SHOW_NORMAL = win32con.SW_SHOWNORMAL
SHOW_MINIMIZED = win32con.SW_SHOWMINNOACTIVE
SHOW_MAXIMIZED = win32con.SW_SHOWMAXIMIZED
SHOW_COMMANDS = (SHOW_NORMAL, SHOW_MINIMIZED, SHOW_MAXIMIZED)

# キーの区切り文字（keymap.MODIFIER_SEPARATOR と同じ。keymap は読み込むと循環 import になるため使わない）
_MODIFIER_SEPARATOR = "+"

# 「管理者として実行」のフラグ（SLDF_RUNAS_USER）
_SLDF_RUNAS_USER = 0x00002000

# 「管理者として実行」を指定できるリンク先の拡張子
_RUN_AS_EXTENSIONS = (".exe", ".com", ".bat", ".cmd", ".msc")

# ショートカットキー（IShellLink の Hotkey）の修飾キー
_HOTKEYF_SHIFT = 0x01
_HOTKEYF_CONTROL = 0x02
_HOTKEYF_ALT = 0x04
_HOTKEY_MODIFIERS = (("CTRL", _HOTKEYF_CONTROL), ("ALT", _HOTKEYF_ALT), ("SHIFT", _HOTKEYF_SHIFT))


def _make_hotkey_key_table():
    """ショートカットキーに使えるキーの名前と仮想キーコードの対応表を作る"""
    table = {}
    for code in range(ord("A"), ord("Z") + 1):
        table[chr(code)] = code
    for code in range(ord("0"), ord("9") + 1):
        table[chr(code)] = code
    for number in range(10):
        table["NUMPAD%d" % number] = win32con.VK_NUMPAD0 + number
    for number in range(1, 25):
        table["F%d" % number] = win32con.VK_F1 + number - 1
    table.update({
        "INSERT": win32con.VK_INSERT,
        "DELETE": win32con.VK_DELETE,
        "HOME": win32con.VK_HOME,
        "END": win32con.VK_END,
        "PAGEUP": win32con.VK_PRIOR,
        "PAGEDOWN": win32con.VK_NEXT,
        "UPARROW": win32con.VK_UP,
        "DOWNARROW": win32con.VK_DOWN,
        "LEFTARROW": win32con.VK_LEFT,
        "RIGHTARROW": win32con.VK_RIGHT,
    })
    return table


# キーの名前（falcon のキー名）→ 仮想キーコード
HOTKEY_KEYS = _make_hotkey_key_table()


class ShortcutInfo:
    """ショートカットの設定"""

    def __init__(self):
        # リンク先のパス。環境変数は展開しない。パスで表せないリンク先（コントロールパネルの項目など）なら空文字列
        self.target = ""
        # パスで表せないリンク先の表示名
        self.target_display_name = ""
        self.arguments = ""
        self.working_directory = ""
        # IShellLink の Hotkey の値。なしなら 0
        self.hotkey = 0
        # SHOW_ のいずれか
        self.show_command = SHOW_NORMAL
        self.description = ""
        self.run_as_admin = False

    def has_path_target(self):
        """リンク先がパスで表されているか"""
        return self.target != ""

    def can_run_as_admin(self):
        """「管理者として実行」を指定できるリンク先か"""
        return os.path.splitext(self.target)[1].lower() in _RUN_AS_EXTENSIONS


def is_shortcut(path: str):
    """ショートカットファイル（.lnk）か"""
    return os.path.splitext(path)[1].lower() == ".lnk" and not os.path.isdir(path)


def _create_link():
    return pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)


def _open(path: str):
    """ショートカットを読み込んだ IShellLink を返す"""
    link = _create_link()
    link.QueryInterface(pythoncom.IID_IPersistFile).Load(path, storagecon.STGM_READ)
    return link


def load(path: str):
    """ショートカットの設定を読み込む。読めなければ pythoncom.com_error。"""
    link = _open(path)
    info = ShortcutInfo()
    info.target = link.GetPath(shell.SLGP_RAWPATH)[0]
    if info.target == "":
        info.target_display_name = _get_id_list_name(link)
    info.arguments = link.GetArguments()
    info.working_directory = link.GetWorkingDirectory()
    info.hotkey = link.GetHotkey()
    show_command = link.GetShowCmd()
    info.show_command = show_command if show_command in SHOW_COMMANDS else SHOW_NORMAL
    info.description = link.GetDescription()
    info.run_as_admin = bool(link.QueryInterface(shell.IID_IShellLinkDataList).GetFlags() & _SLDF_RUNAS_USER)
    return info


def _get_id_list_name(link):
    """パスで表せないリンク先の表示名を返す"""
    try:
        id_list = link.GetIDList()
        if not id_list:
            return ""
        return shell.SHGetDesktopFolder().GetDisplayNameOf(id_list, shellcon.SHGDN_NORMAL)
    except pythoncom.com_error:
        return ""


def save(path: str, info: ShortcutInfo):
    """
    ショートカットの設定を書き込む。失敗したら pythoncom.com_error。
    リンク先は、変わっていなければ設定し直さない（パスで表せないリンク先や、環境変数を含むリンク先をそのまま残すため）。
    """
    link = _open(path)
    if info.has_path_target() and info.target != link.GetPath(shell.SLGP_RAWPATH)[0]:
        link.SetPath(info.target)
    link.SetArguments(info.arguments)
    link.SetWorkingDirectory(info.working_directory)
    link.SetHotkey(info.hotkey)
    link.SetShowCmd(info.show_command)
    link.SetDescription(info.description)
    data_list = link.QueryInterface(shell.IID_IShellLinkDataList)
    flags = data_list.GetFlags()
    if info.run_as_admin:
        flags |= _SLDF_RUNAS_USER
    else:
        flags &= ~_SLDF_RUNAS_USER
    data_list.SetFlags(flags)
    link.QueryInterface(pythoncom.IID_IPersistFile).Save(path, True)


def target_exists(target: str):
    """リンク先が存在するか。環境変数は展開して調べる"""
    return os.path.lexists(os.path.expandvars(target))


def hotkey_to_string(hotkey: int):
    """Hotkey の値を「CTRL+ALT+A」の形の文字列にする。なしなら空文字列"""
    if hotkey == 0:
        return ""
    key_code = hotkey & 0xff
    modifiers = hotkey >> 8
    names = [name for name, flag in _HOTKEY_MODIFIERS if modifiers & flag]
    key_name = next((name for name, code in HOTKEY_KEYS.items() if code == key_code), None)
    names.append(key_name if key_name is not None else "0x%02X" % key_code)
    return _MODIFIER_SEPARATOR.join(names)


def string_to_hotkey(key_string: str):
    """「CTRL+ALT+A」の形の文字列を Hotkey の値にする。空文字列なら 0。使えないキーなら ValueError"""
    if key_string == "":
        return 0
    modifiers = 0
    key_code = None
    for name in key_string.upper().split(_MODIFIER_SEPARATOR):
        flag = dict(_HOTKEY_MODIFIERS).get(name)
        if flag is not None:
            modifiers |= flag
        elif name in HOTKEY_KEYS and key_code is None:
            key_code = HOTKEY_KEYS[name]
        else:
            raise ValueError(key_string)
    if key_code is None:
        raise ValueError(key_string)
    return (modifiers << 8) | key_code


class HotkeyFilter:
    """
    ショートカットのショートカットキーとして使えるキーかを判定する。
    views.keyConfig.KeyInputWindow にキーフィルタとして渡す。
    エクスプローラーと同じく、Ctrl・Alt・Shift のうち2つ以上と、英数字などのキーの組み合わせだけを使える。
    """

    def __init__(self):
        self.last_error = ""

    def check(self, key_string: str):
        """使えるキーの組み合わせかを返す。使えない場合は last_error に理由が入る"""
        self.last_error = ""
        names = key_string.upper().split(_MODIFIER_SEPARATOR)
        modifier_names = dict(_HOTKEY_MODIFIERS)
        keys = [name for name in names if name not in modifier_names]
        modifier_count = len(names) - len(keys)
        if len(keys) != 1 or keys[0] not in HOTKEY_KEYS:
            self.last_error = _("ショートカットキーには、英字・数字・ファンクションキーなどを1つ指定してください。")
            return False
        if modifier_count < 2:
            self.last_error = _("ショートカットキーは、Ctrl・Alt・Shift のうち2つ以上と組み合わせて指定してください。")
            return False
        return True

    def get_usable_keys(self):
        """押されているかを調べるキーの名前の一覧を返す"""
        return [name for name, flag in _HOTKEY_MODIFIERS] + list(HOTKEY_KEYS.keys())
