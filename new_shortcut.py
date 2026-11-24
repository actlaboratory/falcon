# -*- coding: utf-8 -*-
# Falcon make new shortcut
# Note: All comments except these top lines will be written in Japanese.

"""
リンク先を入力して新しいショートカットを作る処理。
エクスプローラーの「新規作成」→「ショートカット」に合わせている。

- リンク先が URL（「https://」など、2文字以上のスキームで始まる）なら、インターネットショートカット（.url）を作る
- 「www.」で始まるものは URL とみなし、先頭に「https://」を付ける
- それ以外はファイル・フォルダのパスとみなし、ショートカット（.lnk）を作る。
  パスの後ろに引数を書ける（「"C:\\Program Files\\a.exe" /x」「notepad a.txt」など）。
  相対パスは作成先のフォルダからの位置とし、フォルダ名のないプログラム名は PATH から探す
"""

import logging
import os
import re
import shutil
import urllib.parse

import pythoncom
from win32com.shell import shell, shellcon

import new_file
import shell_new

log = logging.getLogger("falcon.newShortcut")

TYPE_LNK = "lnk"
TYPE_URL = "url"

_EXTENSIONS = {TYPE_LNK: ".lnk", TYPE_URL: ".url"}

# 「C:」のようなドライブ名と区別するため、スキームは2文字以上とする
_URL_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]+:")

# 名前に使えない文字
_INVALID_NAME_CHARS = re.compile(r"[\\/:*?\"<>|]")

# URL に書いてよい文字（表示できる ASCII 文字）。これ以外はパーセントエンコードする
_URL_SAFE_CHARS = "".join(chr(c) for c in range(0x21, 0x7f))

# アクセス拒否の HRESULT（0x80070005）
_E_ACCESSDENIED = -2147024891


class NewShortcutRequest:
    """作成するショートカットの内容"""

    def __init__(self, name: str, link_type: str, target: str, arguments: str = "", working_directory: str = ""):
        # 拡張子を含むファイル名
        self.name = name
        # TYPE_LNK か TYPE_URL
        self.link_type = link_type
        # リンク先のパスまたは URL
        self.target = target
        # 引数と作業フォルダー（TYPE_LNK だけ）
        self.arguments = arguments
        self.working_directory = working_directory


def is_url(text: str):
    """入力されたリンク先が URL か"""
    text = text.strip()
    return _URL_PATTERN.match(text) is not None or text.lower().startswith("www.")


def make_request(directory: str, target_text: str, name: str):
    """
    入力内容から NewShortcutRequest を作る。
    リンク先が見つからないなど、作れなければ ValueError（利用者に見せるメッセージ）。
    """
    target_text = target_text.strip()
    if target_text == "":
        raise ValueError(_("リンク先を入力してください。"))
    if is_url(target_text):
        request = _make_url_request(target_text)
    else:
        request = _make_lnk_request(directory, target_text)
    name = name.strip()
    if name == "":
        name = _make_unique_name(directory, _default_base_name(request), _EXTENSIONS[request.link_type])
    elif not name.lower().endswith(_EXTENSIONS[request.link_type]):
        name += _EXTENSIONS[request.link_type]
    error = new_file.validate(directory, name)
    if error != "":
        raise ValueError(error)
    request.name = name
    return request


def _make_url_request(text: str):
    """URL のリンク先から NewShortcutRequest を作る"""
    if text.lower().startswith("www."):
        text = "https://" + text
    # .url は ini 形式で、ASCII 以外の文字をそのまま書くと文字化けするため、パーセントエンコードする
    url = urllib.parse.quote(text, safe=_URL_SAFE_CHARS)
    return NewShortcutRequest("", TYPE_URL, url)


def _make_lnk_request(directory: str, text: str):
    """ファイル・フォルダのリンク先から NewShortcutRequest を作る"""
    # まず全体を1つのパスとして探し、なければプログラムと引数に分ける
    target = _find_target(directory, text.strip("\""))
    arguments = ""
    if target is None:
        program, arguments = new_file.split_command(text)
        target = _find_target(directory, program)
        if target is None:
            target = _find_program(program)
    if target is None:
        raise ValueError(_("リンク先が見つかりません。ファイルやフォルダのパス、または URL を入力してください。") + "\n" + text)
    working_directory = "" if os.path.isdir(_native_path(target)) else os.path.dirname(target)
    return NewShortcutRequest("", TYPE_LNK, target, arguments, working_directory)


def _expand(path: str):
    """
    環境変数を展開する。%ProgramFiles% は 64bit 用のフォルダにする。
    ショートカットに保存するパスなので、System32 は Sysnative に置き換えない。
    """
    path = shell_new.expand_path(path)
    sysnative = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Sysnative")
    if os.path.normcase(path).startswith(os.path.normcase(sysnative + "\\")):
        path = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32") + path[len(sysnative):]
    return path


def _native_path(path: str):
    """
    falcon は 32bit で動くため、System32 の中を見るとSysWOW64 になる。
    存在の確認などに使う、64bit 用の本当のパスを返す。
    """
    return shell_new.expand_path(path)


def _find_target(directory: str, path: str):
    """パスのファイル・フォルダがあればフルパスを返す。なければ None。"""
    if path == "":
        return None
    path = _expand(path)
    # 「C:」だけだとそのドライブのカレントディレクトリになってしまうので、ルートにする
    if re.match(r"^[A-Za-z]:$", path):
        path += "\\"
    if not os.path.isabs(path):
        path = os.path.join(directory, path)
    path = os.path.normpath(path)
    if os.path.exists(_native_path(path)):
        return path
    return None


def _find_program(program: str):
    """フォルダ名のないプログラム名を PATH から探してフルパスを返す。なければ None。"""
    if program == "" or os.path.dirname(program) != "":
        return None
    found = shutil.which(_expand(program))
    if found is None:
        # 32bit からは見えない、64bit の System32 にだけあるプログラム
        sysnative = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Sysnative")
        if os.path.isdir(sysnative):
            found = shutil.which(program, path=sysnative)
            if found is not None:
                found = _expand(found)
    return os.path.normpath(found) if found is not None else None


def _default_base_name(request: NewShortcutRequest):
    """名前が入力されなかったときのファイル名（拡張子を除く）"""
    if request.link_type == TYPE_URL:
        host = urllib.parse.urlsplit(request.target).hostname
        name = host if host else _("新しいインターネット ショートカット")
    else:
        name = _get_display_name(request.target)
    name = _INVALID_NAME_CHARS.sub("", name).strip().rstrip(".")
    return name if name != "" else _("新しいショートカット")


def _get_display_name(path: str):
    """リンク先の表示名を返す。ファイルなら拡張子を除く。"""
    native = _native_path(path)
    if os.path.isfile(native):
        return os.path.splitext(os.path.basename(path))[0]
    base = os.path.basename(path.rstrip("\\"))
    if base != "":
        return base
    # ドライブのルートなど
    try:
        dummy, info = shell.SHGetFileInfo(native, 0, shellcon.SHGFI_DISPLAYNAME)
        if info[3]:
            return info[3]
    except Exception:
        pass
    return path


def _make_unique_name(directory: str, base: str, extension: str):
    """同じ名前があれば「名前 (2).lnk」のように番号を付ける"""
    name = base + extension
    number = 2
    while os.path.lexists(os.path.join(directory, name)):
        name = "%s (%d)%s" % (base, number, extension)
        number += 1
    return name


def create(directory: str, request: NewShortcutRequest):
    """ショートカットを作る。既存のファイルは上書きしない。失敗したらエラーメッセージを、成功したら空文字列を返す。"""
    path = os.path.join(directory, request.name)
    if os.path.lexists(path):
        return _("同じ名前のファイルまたはフォルダが既にあります。")
    try:
        if request.link_type == TYPE_URL:
            _create_url(path, request.target)
        else:
            _create_lnk(path, request)
    except FileExistsError:
        return _("同じ名前のファイルまたはフォルダが既にあります。")
    except PermissionError:
        return _access_denied_message()
    except FileNotFoundError:
        return _("作成先のフォルダが見つかりません。")
    except pythoncom.com_error as e:
        if e.hresult == _E_ACCESSDENIED:
            return _access_denied_message()
        log.warning("cannot create shortcut %s: %s" % (path, e))
        detail = str(e.args[1]) if len(e.args) > 1 and e.args[1] else str(e)
        return _("ショートカットを作成できませんでした。") + "\n" + detail
    except OSError as e:
        log.warning("cannot create shortcut %s: %s" % (path, e))
        detail = e.strerror if e.strerror else str(e)
        return _("ショートカットを作成できませんでした。") + "\n" + detail
    return ""


def _access_denied_message():
    """アクセス拒否のときのメッセージ"""
    return _("アクセスが拒否されました。この場所にファイルを作成する権限がないか、読み取り専用の場所です。")


def _create_url(path: str, url: str):
    """インターネットショートカット（.url）を作る"""
    content = "[InternetShortcut]\r\nURL=%s\r\n" % url
    created = False
    try:
        with open(path, "x", encoding="ascii", newline="") as f:
            created = True
            f.write(content)
    except OSError:
        # 書き込みの途中で失敗したら、作りかけのファイルを消す。自分で作ったファイル以外は消さない
        if created:
            try:
                os.remove(path)
            except OSError:
                pass
        raise


def _create_lnk(path: str, request: NewShortcutRequest):
    """ショートカット（.lnk）を作る"""
    link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    link.SetPath(request.target)
    if request.arguments != "":
        link.SetArguments(request.arguments)
    if request.working_directory != "":
        link.SetWorkingDirectory(request.working_directory)
    link.QueryInterface(pythoncom.IID_IPersistFile).Save(path, True)
