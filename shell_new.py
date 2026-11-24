# -*- coding: utf-8 -*-
# Falcon ShellNew registry reader
# Note: All comments except these top lines will be written in Japanese.

"""
エクスプローラーの「新規作成」メニューに出る項目を、レジストリの ShellNew キーから読み込む。

HKEY_CLASSES_ROOT\\.拡張子\\ShellNew または HKEY_CLASSES_ROOT\\.拡張子\\(ProgID)\\ShellNew に、次のいずれかの値で作り方が書かれている。
- NullFile: 空のファイルを作る
- Data: 値の内容をそのまま書き込む
- FileName: ひな形のファイルをコピーする
- Command: コマンドを実行する（作るのは起動したプログラム）
- Handler: COM のハンドラで作る（falcon では対応しない）
"""

import ctypes
import logging
import os
import re
import winreg

from win32com.shell import shell, shellcon

log = logging.getLogger("falcon.shellNew")

METHOD_NULL_FILE = "null_file"
METHOD_DATA = "data"
METHOD_TEMPLATE = "template"
METHOD_COMMAND = "command"

# レジストリに登録されていても一覧に出さない拡張子
# .contact は Windows の古い「連絡先」機能のもので、エクスプローラーの新規作成メニューにも出ない
_EXCLUDED_EXTENSIONS = {".contact"}


class ShellNewEntry:
    """ShellNew に登録された作成方法1件"""

    def __init__(self, extension: str, type_name: str, item_name: str, method: str, value):
        # ピリオドを含む拡張子
        self.extension = extension
        # 種類の名前（MenuText、なければファイルの種類の名前）
        self.type_name = type_name
        # 新しいファイルの既定の名前（拡張子を除く）。ItemName がなければ空文字列
        self.item_name = item_name
        # METHOD_ のいずれか
        self.method = method
        # 作成方法ごとの値。METHOD_DATA なら bytes、METHOD_TEMPLATE ならひな形のフルパス、METHOD_COMMAND ならコマンドライン
        self.value = value


def expand_path(path: str):
    """
    環境変数を展開する。
    falcon は 32bit で動くため、%ProgramFiles% などがそのままでは 32bit 用のフォルダになる。64bit 用のフォルダに置き換える。
    """
    for name, native in (("CommonProgramFiles", "CommonProgramW6432"), ("ProgramFiles", "ProgramW6432")):
        if native in os.environ:
            path = re.sub("%" + name + "%", lambda m: os.environ[native], path, flags=re.IGNORECASE)
    path = os.path.expandvars(path)
    # 32bit のプログラムから System32 を見ると SysWOW64 に置き換えられるので、Sysnative 経由で見る
    system32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
    sysnative = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Sysnative")
    if os.path.isdir(sysnative) and os.path.normcase(path).startswith(os.path.normcase(system32 + "\\")):
        path = sysnative + path[len(system32):]
    return path


def get_entries():
    """ShellNew に登録された、falcon で作成できる項目の一覧を、種類の名前の順に返す"""
    entries = []
    index = 0
    while True:
        try:
            name = winreg.EnumKey(winreg.HKEY_CLASSES_ROOT, index)
        except OSError:
            break
        index += 1
        if not name.startswith(".") or len(name) < 2:
            continue
        if name.lower() in _EXCLUDED_EXTENSIONS:
            continue
        try:
            entry = _read_entry(name)
        except OSError as e:
            log.warning("cannot read ShellNew of %s: %s" % (name, e))
            continue
        if entry is not None:
            entries.append(entry)
    entries.sort(key=lambda e: e.type_name.lower())
    return entries


def _read_entry(extension: str):
    """拡張子の ShellNew を読む。作成できるものがなければ None。"""
    with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, extension) as ext_key:
        values = _find_shell_new(ext_key)
    if values is None:
        return None
    # ショートカットやライブラリなど、COM のハンドラで作る項目は対応しない
    if "handler" in values:
        return None

    if "command" in values:
        method, value = METHOD_COMMAND, str(values["command"][0])
    elif "filename" in values:
        template = _find_template(str(values["filename"][0]))
        if template is None:
            return None
        method, value = METHOD_TEMPLATE, template
    elif "data" in values:
        method, value = METHOD_DATA, _data_to_bytes(*values["data"])
    elif "nullfile" in values:
        method, value = METHOD_NULL_FILE, None
    else:
        return None

    type_name = _load_indirect_string(values.get("menutext", ("", 0))[0]) or _get_type_name(extension)
    item_name = _load_indirect_string(values.get("itemname", ("", 0))[0])
    return ShellNewEntry(extension, type_name, item_name, method, value)


def _find_shell_new(ext_key):
    """拡張子のキーから ShellNew キーを探し、値を {小文字の名前: (値, 型)} で返す。なければ None。"""
    candidates = []
    try:
        prog_id = winreg.QueryValueEx(ext_key, "")[0]
        if isinstance(prog_id, str) and prog_id != "":
            candidates.append(prog_id + "\\ShellNew")
    except OSError:
        pass
    candidates.append("ShellNew")
    for sub_key in candidates:
        try:
            with winreg.OpenKey(ext_key, sub_key) as key:
                return _read_values(key)
        except OSError:
            continue
    return None


def _read_values(key):
    """キーのすべての値を {小文字の名前: (値, 型)} で返す"""
    values = {}
    index = 0
    while True:
        try:
            name, value, value_type = winreg.EnumValue(key, index)
        except OSError:
            break
        index += 1
        if value_type == winreg.REG_EXPAND_SZ and isinstance(value, str):
            value = expand_path(value)
        values[name.lower()] = (value, value_type)
    return values


def _data_to_bytes(value, value_type):
    """Data の値を、ファイルに書き込む bytes にする"""
    if isinstance(value, bytes):
        return value
    if value is None:
        return b""
    # 文字列は ANSI のコードページで書き込む（エクスプローラーと同じ）
    return str(value).encode("mbcs", errors="replace")


def _find_template(file_name: str):
    """FileName で指定されたひな形を探してフルパスを返す。見つからなければ None。"""
    file_name = expand_path(file_name)
    if os.path.isabs(file_name):
        return file_name if os.path.isfile(file_name) else None
    folders = []
    for csidl in (shellcon.CSIDL_TEMPLATES, shellcon.CSIDL_COMMON_TEMPLATES):
        try:
            folders.append(shell.SHGetFolderPath(0, csidl, None, 0))
        except Exception:
            continue
    folders.append(expand_path(r"%SystemRoot%\ShellNew"))
    for folder in folders:
        path = os.path.join(folder, file_name)
        if os.path.isfile(path):
            return path
    return None


def _load_indirect_string(value):
    """「@ファイル名,-ID」形式の文字列を読み込む。そのほかの文字列はそのまま返す。失敗したら空文字列。"""
    if not isinstance(value, str) or value == "":
        return ""
    if not value.startswith("@"):
        return value
    buffer = ctypes.create_unicode_buffer(1024)
    result = ctypes.windll.shlwapi.SHLoadIndirectString(value, buffer, len(buffer), None)
    if result != 0:
        return ""
    return buffer.value


def _get_type_name(extension: str):
    """拡張子からファイルの種類の名前（「Microsoft Word 文書」など）を返す"""
    try:
        dummy, info = shell.SHGetFileInfo(
            extension, 0x80, shellcon.SHGFI_TYPENAME | shellcon.SHGFI_USEFILEATTRIBUTES)
        if info[4]:
            return info[4]
    except Exception:
        pass
    return extension[1:].upper()
