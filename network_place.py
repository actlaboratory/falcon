# -*- coding: utf-8 -*-
# Falcon network place
# Note: All comments except these top lines will be written in Japanese.

r"""
ネットワークの場所（エクスプローラーの「PC」に表示される、ネットワーク上のフォルダへのショートカット）の読み書きです。

ネットワークの場所は、%APPDATA%\Microsoft\Windows\Network Shortcuts に、次の内容のフォルダとして保存されています。
エクスプローラーの「ネットワークの場所を追加する」で作られるものと同じ形で作ります。
- desktop.ini（フォルダのショートカットであることを示す。隠し・システム属性）
- target.lnk（リンク先へのショートカット）
- フォルダ自体には読み取り専用属性を付ける（desktop.ini を有効にするため）

FTP・FTPS・SFTP の場所は、Windows のネットワークの場所では SFTP を扱えず、FTP もパスで表せないため、
falcon の設定（remote_places セクション、名前 → URL）に保存します。
"""

import logging
import os
import shutil
import stat

import pythoncom
import pywintypes
import win32api
import win32con
from win32com.shell import shell, shellcon

import fileSystemManager
import globalVars
import network_drive
import remote_storage
import shortcut_link

log = logging.getLogger("falcon.network_place")

_TARGET_NAME = "target.lnk"
_DESKTOP_INI_NAME = "desktop.ini"
# フォルダのショートカットを表すシェルの CLSID
_DESKTOP_INI = "[.ShellClassInfo]\r\nCLSID2={0AFACED1-E828-11D1-9187-B532F1E9575D}\r\nFlags=2\r\n"
# FTP・SFTP の場所を保存する設定のセクション
_REMOTE_SECTION = "remote_places"


class NetworkPlace:
    """ネットワークの場所"""

    def __init__(self, name, folder, target):
        # 表示名
        self.name = name
        # ネットワークの場所を保存しているフォルダのフルパス。falcon の設定に保存した FTP・SFTP の場所は None
        self.folder = folder
        # リンク先（\\server\share や sftp://server/path など）
        self.target = target


def get_directory():
    """ネットワークの場所を保存するフォルダのパスを返す。"""
    return shell.SHGetFolderPath(0, shellcon.CSIDL_NETHOOD, None, 0)


def get_places():
    """
    ネットワークの場所の一覧を返す。falcon で開けない場所（エクスプローラーで追加した FTP、Webサイトなど）は含めない。
    リンク先には接続しないので、すぐに返る。
    """
    places = []
    try:
        directory = get_directory()
        names = os.listdir(directory)
    except (OSError, pywintypes.com_error) as err:
        log.warning("Cannot list network places: %s" % err)
        names = []
    for name in names:
        folder = os.path.join(directory, name)
        link = os.path.join(folder, _TARGET_NAME)
        if not os.path.isfile(link):
            continue
        try:
            target = shortcut_link.load(link).target
        except pythoncom.com_error as err:
            log.warning("Cannot read the network place %s: %s" % (name, err))
            continue
        # FTP や Web サイトの場所は、リンク先をパスで表せない
        if target == "" or not network_drive.validate_folder_path(target.rstrip("\\"), allow_server=True) == "":
            continue
        places.append(NetworkPlace(name, folder, target.rstrip("\\")))
    for name, url in _get_remote_places().items():
        places.append(NetworkPlace(name, None, url))
    return places


def _get_remote_places():
    """falcon の設定に保存した FTP・SFTP の場所（名前 → URL）"""
    return globalVars.app.settings.get_section(_REMOTE_SECTION)


def find_name(target):
    """リンク先が target のネットワークの場所の名前を返す。なければ空文字列"""
    for place in get_places():
        if place.target.rstrip("/\\").lower() == target.rstrip("/\\").lower():
            return place.name
    return ""


def get_default_name(target):
    r"""
    リンク先から、ネットワークの場所の名前の初期値を作る。
    \\NAS\public なら「public (NAS)」、sftp://server/home/user なら「user (server)」。
    """
    if remote_storage.is_remote_url(target):
        location = remote_storage.parse_url(target)
        folder = location.path.rstrip("/").rsplit("/", 1)[-1]
        return "%s (%s)" % (folder, location.host) if folder else location.host
    names = target[2:].split("\\")
    if len(names) < 2:
        return names[0]
    return "%s (%s)" % (names[-1], names[0])


def validate_name(name):
    """ネットワークの場所の名前に問題があればその説明を、なければ空文字列を返す。"""
    if name == "":
        return _("名前を入力してください。")
    # 「a:b」のような名前を os.path.join に渡すとドライブ名と解釈されるため、文字列をつなげる
    path = get_directory() + "\\" + name
    error = fileSystemManager.ValidationObjectName(path, fileSystemManager.pathTypes.DIRECTORY, name)
    if error:
        return error
    if _exists(name):
        return _("同じ名前のネットワークの場所が既にあります。")
    return ""


def _exists(name):
    """同じ名前（大文字と小文字は区別しない）のネットワークの場所があるかどうか"""
    if os.path.lexists(os.path.join(get_directory(), name)):
        return True
    return name.lower() in (key.lower() for key in _get_remote_places())


def make_unique_name(name):
    """同じ名前のネットワークの場所があれば、「名前 (2)」のように番号を付けた名前を返す。"""
    result = name
    number = 2
    while _exists(result):
        result = "%s (%d)" % (name, number)
        number += 1
    return result


def add(name, target):
    """
    ネットワークの場所を追加する。target は UNC パスか、FTP・SFTP の URL。
    失敗した場合は OSError または pythoncom.com_error になる。途中まで作ったものは消す。
    """
    if remote_storage.is_remote_url(target):
        places = _get_remote_places()
        places[name] = target
        globalVars.app.settings.replace_section(_REMOTE_SECTION, places)
        log.info("added remote place %s (%s)" % (name, target))
        return
    folder = os.path.join(get_directory(), name)
    os.mkdir(folder)
    try:
        ini_path = os.path.join(folder, _DESKTOP_INI_NAME)
        with open(ini_path, "w", encoding="utf-8", newline="") as f:
            f.write(_DESKTOP_INI)
        win32api.SetFileAttributes(ini_path, win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM)
        link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
        link.SetPath(target)
        link.QueryInterface(pythoncom.IID_IPersistFile).Save(os.path.join(folder, _TARGET_NAME), True)
        win32api.SetFileAttributes(folder, win32con.FILE_ATTRIBUTE_READONLY)
    except (OSError, pywintypes.error, pythoncom.com_error):
        _remove_folder(folder)
        raise
    log.info("added network place %s (%s)" % (name, target))


def remove(name, folder):
    """
    ネットワークの場所を削除する。folder は保存しているフォルダで、falcon の設定に保存した FTP・SFTP の場所なら None。
    失敗した場合は OSError になる。
    """
    if folder is None:
        places = _get_remote_places()
        places.pop(name, None)
        globalVars.app.settings.replace_section(_REMOTE_SECTION, places)
        log.info("removed remote place %s" % name)
        return
    # 他のフォルダを誤って消さないよう、ネットワークの場所の保存先の直下だけを対象にする
    if os.path.normcase(os.path.dirname(folder)) != os.path.normcase(get_directory()):
        raise ValueError("not a network place: %s" % folder)
    _remove_folder(folder)
    log.info("removed network place %s" % folder)


def _remove_folder(folder):
    """読み取り専用・システム属性を外しながら、フォルダを中身ごと削除する。"""
    def on_error(func, path, exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    if not os.path.isdir(folder):
        return
    os.chmod(folder, stat.S_IWRITE)
    shutil.rmtree(folder, onexc=on_error)
