# -*- coding: utf-8 -*-
# Falcon network resource utilities
# Note: All comments except these top lines will be written in Japanese.

"""
ネットワーク上のコンピューターと共有フォルダを調べる処理と、接続時の認証の処理です。

コンピューターの列挙には、エクスプローラーの「ネットワーク」と同じシェルフォルダを使います。
WNetOpenEnum による列挙は SMB1 と Computer Browser サービスに依存しており、現在の Windows では何も見つかりません。
"""

import logging
import os

import pythoncom
import pywintypes
import win32netcon
import win32wnet
from win32com.shell import shell, shellcon

log = logging.getLogger("falcon.network_resource")

# 資格情報を入力して接続し直せば解決する可能性があるエラー
_AUTH_ERRORS = frozenset((
    5,  # ERROR_ACCESS_DENIED
    86,  # ERROR_INVALID_PASSWORD
    1326,  # ERROR_LOGON_FAILURE
    1327,  # ERROR_ACCOUNT_RESTRICTION
    1331,  # ERROR_ACCOUNT_DISABLED
    1385,  # ERROR_LOGON_TYPE_NOT_GRANTED
))
_ERROR_CANCELLED = 1223
_CONNECT_INTERACTIVE = 0x8
_ENUM_COUNT = 64  # WNetEnumResource に65以上は指定できない


def is_unc_path(path):
    r"""\\server や \\server\share\... の形式のパスかどうかを返す。"""
    return path.startswith("\\\\") and not path.startswith(("\\\\?\\", "\\\\.\\"))


def is_server_path(path):
    r"""共有名を含まない、\\server の形式のパスかどうかを返す。末尾の \ は無視する。"""
    if not is_unc_path(path):
        return False
    name = path[2:].rstrip("\\")
    return name != "" and "\\" not in name


def split_share_root(path):
    r"""パスが共有のルート(\\server\share)なら (\\server, share) を返す。違う場合は None を返す。"""
    if not is_unc_path(path):
        return None
    parts = path[2:].rstrip("\\").split("\\")
    if len(parts) != 2 or "" in parts:
        return None
    return "\\\\" + parts[0], parts[1]


def get_server_path(path):
    r"""UNCパスから、\\server の部分を取り出す。"""
    return "\\\\" + path[2:].split("\\")[0]


def enumerate_computers(on_found, is_canceled):
    r"""
    ネットワーク上のコンピューターを探し、見つかるたびに on_found(名前, \\serverの形式のパス, hIcon) を呼ぶ。
    終わるまでに数十秒かかるため、別スレッドで呼ぶこと。
    取得できなかった場合は pywintypes.com_error になる。中断された場合は False を返す。
    """
    pythoncom.CoInitialize()
    try:
        return _enumerate_computers(on_found, is_canceled)
    finally:
        pythoncom.CoUninitialize()


def _enumerate_computers(on_found, is_canceled):
    """enumerate_computers の本体。COMのオブジェクトを CoUninitialize の前に解放するために分けている。"""
    root_pidl = shell.SHGetSpecialFolderLocation(0, shellcon.CSIDL_NETWORK)
    folder = shell.SHGetDesktopFolder().BindToObject(root_pidl, None, shell.IID_IShellFolder)
    enumerator = folder.EnumObjects(0, shellcon.SHCONTF_FOLDERS | shellcon.SHCONTF_NONFOLDERS)
    found = set()
    while enumerator is not None and not is_canceled():
        pidls = enumerator.Next(1)
        if not pidls:
            break
        try:
            path = folder.GetDisplayNameOf(pidls[0], shellcon.SHGDN_FORPARSING)
            # ルーターやメディア機器などは、フォルダとして開けないので含めない
            if not is_server_path(path) or path.lower() in found:
                continue
            name = folder.GetDisplayNameOf(pidls[0], shellcon.SHGDN_NORMAL)
        except pywintypes.com_error as err:
            log.warning("Cannot get the name of a network item: %s" % err)
            continue
        found.add(path.lower())
        # パスではなくPIDLを指定して、コンピューターに接続せずにアイコンを取得する
        dummy, info = shell.SHGetFileInfo(root_pidl + pidls[0], 0, shellcon.SHGFI_PIDL | shellcon.SHGFI_ICON)
        if is_canceled():
            return False
        on_found(name, path, info[0])
    return not is_canceled()


def get_shares(server):
    r"""
    コンピューター(\\server)で公開されている共有フォルダのパスの一覧を返す。
    取得できなかった場合は pywintypes.error になる。
    """
    resource = win32wnet.NETRESOURCE()
    resource.lpRemoteName = server
    handle = win32wnet.WNetOpenEnum(win32netcon.RESOURCE_GLOBALNET, win32netcon.RESOURCETYPE_DISK, 0, resource)
    shares = []
    try:
        while True:
            items = win32wnet.WNetEnumResource(handle, _ENUM_COUNT)
            if not items:
                break
            shares.extend(item.lpRemoteName for item in items if item.lpRemoteName)
    finally:
        win32wnet.WNetCloseEnum(handle)
    return shares


def get_shares_with_auth(server, hwnd):
    """get_shares と同じだが、認証が必要な場合は資格情報の入力画面を出す。"""
    try:
        return get_shares(server)
    except pywintypes.error as err:
        if err.winerror not in _AUTH_ERRORS:
            raise
    _connect(server + "\\IPC$", win32netcon.RESOURCETYPE_ANY, hwnd)
    return get_shares(server)


def exists_with_auth(path, hwnd):
    """
    パスが存在するかどうかを返す。UNCパスで認証が必要な場合は、資格情報の入力画面を出す。
    利用者が入力をやめた場合や接続できなかった場合は pywintypes.error になる。
    """
    try:
        os.stat(path)
        return True
    except ValueError:
        return False
    except OSError as err:
        if not is_unc_path(path) or err.winerror not in _AUTH_ERRORS:
            return False
    share = os.path.splitdrive(path)[0]
    _connect(share, win32netcon.RESOURCETYPE_DISK, hwnd)
    return os.path.exists(path)


def is_cancelled_error(err):
    """利用者が資格情報の入力をやめたことによるエラーかどうかを返す。"""
    return err.winerror == _ERROR_CANCELLED


def _connect(remote_name, resource_type, hwnd):
    """ドライブを割り当てずに接続する。必要な場合は、Windowsの資格情報の入力画面が出る。"""
    resource = win32wnet.NETRESOURCE()
    resource.dwType = resource_type
    resource.lpRemoteName = remote_name
    win32wnet.WNetAddConnection3(hwnd, resource, None, None, _CONNECT_INTERACTIVE)
