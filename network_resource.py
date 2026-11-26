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
import win32file
import win32netcon
import win32wnet
from win32com.shell import shell, shellcon

import background_wait

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
# ネットワークや接続先の機器に接続できないことを示すエラー
_CONNECTION_ERRORS = frozenset((
    51,  # ERROR_REM_NOT_LIST
    53,  # ERROR_BAD_NETPATH
    54,  # ERROR_NETWORK_BUSY
    55,  # ERROR_DEV_NOT_EXIST
    58,  # ERROR_BAD_NET_RESP
    59,  # ERROR_UNEXP_NET_ERR
    64,  # ERROR_NETNAME_DELETED
    121,  # ERROR_SEM_TIMEOUT
    1203,  # ERROR_NO_NET_OR_BAD_PATH
    1222,  # ERROR_NO_NETWORK
    1225,  # ERROR_CONNECTION_REFUSED
    1231,  # ERROR_NETWORK_UNREACHABLE
    1232,  # ERROR_HOST_UNREACHABLE
    1233,  # ERROR_PROTOCOL_UNREACHABLE
    1234,  # ERROR_PORT_UNREACHABLE
    1236,  # ERROR_CONNECTION_ABORTED
    1256,  # ERROR_HOST_DOWN
    2250,  # ERROR_NOT_CONNECTED
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


class PathStatus:
    """パスを調べた結果"""

    def __init__(self, exists, is_file=False, error_code=0, message=""):
        self.exists = exists
        self.is_file = is_file
        # 存在を確認できなかった場合の、Windowsのエラーコードとその説明
        self.error_code = error_code
        self.message = message

    def is_connection_error(self):
        """ネットワークに接続できないために、存在を確認できなかったかどうかを返す。"""
        return is_connection_error(self.error_code)


def is_connection_error(error_code):
    """Windowsのエラーコードが、ネットワークに接続できないことを示すものかどうかを返す。"""
    return error_code in _CONNECTION_ERRORS


def is_auth_error(error_code):
    """Windowsのエラーコードが、資格情報を入力して接続し直せば解決する可能性があるものかどうかを返す。"""
    return error_code in _AUTH_ERRORS


def get_connection_error_message(path, message):
    """ネットワークに接続できないことを利用者に知らせる文を返す。message はWindowsのエラーの説明。"""
    return _("ネットワークに接続できないため、%(path)s を開けませんでした。\nWi-Fiなどのネットワークの接続と、接続先の機器の状態を確認してください。\n(%(error)s)") % {
        "path": path, "error": message}


def is_remote_path(path):
    """UNCパス、または接続中のネットワークドライブのパスかどうかを返す。"""
    if is_unc_path(path):
        return True
    return win32file.GetDriveType(os.path.splitdrive(path)[0] + "\\") == win32file.DRIVE_REMOTE


def _get_status(path):
    """(別スレッド)パスを調べて PathStatus を返す。"""
    try:
        os.stat(path)
    except ValueError:
        return PathStatus(False)
    except OSError as err:
        return PathStatus(False, error_code=err.winerror or 0, message=err.strerror or "")
    return PathStatus(True, is_file=os.path.isfile(path))


def _check_path(task, path):
    """(別スレッド)パスを調べて PathStatus を返す。"""
    status = _get_status(path)
    if status.exists or status.is_connection_error() or status.error_code in _AUTH_ERRORS:
        return status
    # 切断されていても「見つからない」というエラーになることがあるので、ドライブや共有フォルダのルートも調べる
    task.check_canceled()
    if is_remote_path(path):
        root_status = _get_status(os.path.splitdrive(path)[0] + "\\")
        if root_status.is_connection_error():
            return root_status
    return status


def check_path(path):
    """パスを別スレッドで調べて PathStatus を返す。利用者が中止した場合は background_wait.Canceled になる。"""
    return background_wait.run(_check_path, path)


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


def get_share_icons_with_auth(server, hwnd):
    """
    get_shares と同じだが、別スレッドで取得し、(共有フォルダのパス, hIcon) の一覧を返す。
    認証が必要な場合は資格情報の入力画面を出す。利用者が中止した場合は background_wait.Canceled になる。
    """
    try:
        return background_wait.run(_get_share_icons, server)
    except pywintypes.error as err:
        if err.winerror not in _AUTH_ERRORS:
            raise
    _connect(server + "\\IPC$", win32netcon.RESOURCETYPE_ANY, hwnd)
    return background_wait.run(_get_share_icons, server)


def _get_share_icons(task, server):
    """(別スレッド)共有フォルダのパスとアイコンの一覧を返す。"""
    result = []
    for share in get_shares(server):
        task.check_canceled()
        dummy, info = shell.SHGetFileInfo(share, 0, shellcon.SHGFI_ICON)
        result.append((share, info[0]))
    return result


def check_path_with_auth(path, hwnd):
    """
    check_path と同じだが、UNCパスで認証が必要な場合は、資格情報の入力画面を出す。
    利用者が入力をやめた場合や接続できなかった場合は pywintypes.error になる。
    """
    status = check_path(path)
    if status.exists or not is_unc_path(path) or status.error_code not in _AUTH_ERRORS:
        return status
    share = os.path.splitdrive(path)[0]
    _connect(share, win32netcon.RESOURCETYPE_DISK, hwnd)
    return check_path(path)


def is_cancelled_error(err):
    """利用者が資格情報の入力をやめたことによるエラーかどうかを返す。"""
    return err.winerror == _ERROR_CANCELLED


def _connect(remote_name, resource_type, hwnd):
    """ドライブを割り当てずに接続する。必要な場合は、Windowsの資格情報の入力画面が出る。"""
    resource = win32wnet.NETRESOURCE()
    resource.dwType = resource_type
    resource.lpRemoteName = remote_name
    win32wnet.WNetAddConnection3(hwnd, resource, None, None, _CONNECT_INTERACTIVE)
