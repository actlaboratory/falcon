# -*- coding: utf-8 -*-
# Falcon paste as shortcut
# Note: All comments except these top lines will be written in Japanese.

"""
クリップボードの項目のショートカットを、指定したフォルダに作る処理。
エクスプローラーの「ショートカットの貼り付け」に合わせている。

- 名前はエクスプローラーと同じ SHGetNewLinkInfo で決める（例: 「a.txt - ショートカット.lnk」。同じ名前があれば「(2)」が付く）
- 項目がショートカット自体なら、ショートカットのショートカットは作らず、そのショートカットをコピーする（SHGetNewLinkInfo の pfMustCopy）
- ファイルへのショートカットは、作業フォルダーにファイルのあるフォルダを入れる。フォルダへのショートカットは空にする
"""

import ctypes
import logging
import os
import shutil
from ctypes import wintypes

import pythoncom
from win32com.shell import shell

log = logging.getLogger("falcon.pasteShortcut")

# SHGetNewLinkInfo のフラグ。「 - ショートカット」を付けた名前にする
_SHGNLI_PREFIXNAME = 0x00000002

_shell32 = ctypes.windll.shell32
_shell32.SHGetNewLinkInfoW.argtypes = [
    wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.POINTER(wintypes.BOOL), wintypes.UINT]
_shell32.SHGetNewLinkInfoW.restype = wintypes.BOOL

# SHGetNewLinkInfo が受け取るバッファの大きさ（MAX_PATH）
_MAX_PATH = 260

# アクセス拒否の HRESULT（0x80070005）
_E_ACCESSDENIED = -2147024891


def _access_denied_message():
    """アクセス拒否のときのメッセージ。翻訳を使うので関数にしている"""
    return _("アクセスが拒否されました。この場所にファイルを作成する権限がないか、読み取り専用の場所です。")


class PasteShortcutResult:
    """ショートカットの貼り付けの結果"""

    def __init__(self):
        # 作った項目の名前
        self.created = []
        # 作れなかった項目の、元のパスとエラーメッセージの組
        self.failed = []


def get_link_name(target: str, directory: str):
    """
    target のショートカットを directory に作るときのパスと、ショートカットを作らずにコピーすべきかを返す。
    名前を決められなければ OSError。
    """
    buffer = ctypes.create_unicode_buffer(_MAX_PATH)
    must_copy = wintypes.BOOL()
    if not _shell32.SHGetNewLinkInfoW(target, directory, buffer, ctypes.byref(must_copy), _SHGNLI_PREFIXNAME):
        raise OSError(_("ショートカットの名前を決められませんでした。"))
    return buffer.value, bool(must_copy.value)


def create_link(path: str, target: str):
    """target を指すショートカットを path に作る。失敗したら例外。"""
    link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
    link.SetPath(target)
    if not os.path.isdir(target):
        link.SetWorkingDirectory(os.path.dirname(target))
    link.QueryInterface(pythoncom.IID_IPersistFile).Save(path, True)


def paste(targets: list, directory: str):
    """targets のそれぞれについて、directory にショートカットを作る。結果を PasteShortcutResult で返す。"""
    result = PasteShortcutResult()
    for target in targets:
        error = _paste_one(target, directory, result)
        if error != "":
            result.failed.append((target, error))
    return result


def _paste_one(target: str, directory: str, result: PasteShortcutResult):
    """1項目分のショートカットを作る。失敗したらエラーメッセージを返す。成功したら空文字列。"""
    if not os.path.lexists(target):
        return _("元の項目が見つかりません。")
    try:
        path, must_copy = get_link_name(target, directory)
    except OSError as e:
        return str(e)
    # SHGetNewLinkInfo は空いている名前を返すが、念のため上書きしないようにする
    if os.path.lexists(path):
        return _("同じ名前のファイルまたはフォルダが既にあります。")
    try:
        if must_copy:
            shutil.copy2(target, path)
        else:
            create_link(path, target)
    except PermissionError:
        return _access_denied_message()
    except pythoncom.com_error as e:
        if e.hresult == _E_ACCESSDENIED:
            return _access_denied_message()
        log.warning("cannot paste shortcut of %s to %s: %s" % (target, path, e))
        return _("ショートカットを作成できませんでした。") + "\n" + _error_detail(e)
    except OSError as e:
        log.warning("cannot paste shortcut of %s to %s: %s" % (target, path, e))
        return _("ショートカットを作成できませんでした。") + "\n" + _error_detail(e)
    result.created.append(os.path.basename(path))
    return ""


def _error_detail(error):
    """例外から、利用者に見せる説明を取り出す"""
    if isinstance(error, pythoncom.com_error):
        # (hresult, 説明, 追加情報, 引数の位置)
        return str(error.args[1]) if len(error.args) > 1 and error.args[1] else str(error)
    return error.strerror if getattr(error, "strerror", None) else str(error)
