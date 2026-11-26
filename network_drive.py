# -*- coding: utf-8 -*-
# Falcon network drive
# Note: All comments except these top lines will be written in Japanese.

"""
ネットワークドライブの割り当てと切断です。

割り当て・切断には WNetAddConnection3 / WNetCancelConnection2 を使います。
接続できない場所を指定すると数十秒戻ってこないことがあるため、
資格情報の入力画面を出す必要がない処理は background_wait で別スレッドで行います。
"""

import logging
import re

import pywintypes
import win32api
import win32netcon
import win32wnet

import background_wait
import network_resource

log = logging.getLogger("falcon.network_drive")

_ERROR_ALREADY_ASSIGNED = 85
_ERROR_SESSION_CREDENTIAL_CONFLICT = 1219
_ERROR_OPEN_FILES = 2401
_ERROR_DEVICE_IN_USE = 2404
_ERROR_NOT_CONNECTED = 2250

# UNCパスのサーバー名・共有名・フォルダ名に使えない文字
_INVALID_CHARS = re.compile(r'[<>:"/|?*\x00-\x1f]')


class MapRequest:
    """ネットワークドライブの割り当ての内容"""

    def __init__(self, letter, remote_path, reconnect=True, use_other_credentials=False):
        # 割り当てるドライブ文字（"Z" など、1文字）
        self.letter = letter
        # 割り当てるフォルダ（\\server\share または \\server\share\folder）
        self.remote_path = remote_path
        # サインイン時に再接続するかどうか
        self.reconnect = reconnect
        # 別の資格情報を使って接続するかどうか
        self.use_other_credentials = use_other_credentials


class DisconnectResult:
    """切断の結果"""

    OK = 0
    # 開いているファイルがあるため切断できなかった（強制的に切断すれば切断できる）
    IN_USE = 1
    # 既に切断されていた
    NOT_CONNECTED = 2


def get_free_letters():
    """使われていないドライブ文字の一覧を、エクスプローラーと同じく Z から順に返す。"""
    used = win32api.GetLogicalDrives()
    return [chr(ord("A") + i) for i in range(25, -1, -1) if not used & (1 << i)]


def normalize_remote_path(text):
    r"""入力されたフォルダのパスを整える。前後の空白と末尾の \ を除き、/ を \ にする。"""
    return text.strip().replace("/", "\\").rstrip("\\")


def validate_folder_path(path, allow_server=False):
    r"""
    ネットワーク上のフォルダのパス（normalize_remote_path で整えたもの）として正しいかを調べる。
    問題があればその説明を、なければ空文字列を返す。allow_server=True の場合は \\server だけでもよい。
    """
    if path == "":
        return _("フォルダを入力してください。")
    if not network_resource.is_unc_path(path):
        return _("フォルダは \\\\サーバー名\\共有名 の形式で入力してください。")
    names = path[2:].split("\\")
    if "" in names:
        return _("フォルダのパスが正しくありません。")
    if _INVALID_CHARS.search(path[2:]):
        return _("フォルダのパスに使えない文字が含まれています。")
    if len(names) < 2 and not allow_server:
        return _("共有名まで入力してください（\\\\サーバー名\\共有名 の形式）。")
    return ""


def get_initial_path(path):
    r"""
    ダイアログに最初に入れておくパスを返す。
    ネットワーク上のフォルダならそのまま、コンピューター(\\server)なら共有名を続けて入力できるよう末尾に \ を付ける。
    それ以外は空文字列。
    """
    if not path or not network_resource.is_unc_path(path):
        return ""
    if network_resource.is_server_path(path):
        return path.rstrip("\\") + "\\"
    return path.rstrip("\\")


def map_drive(request, hwnd):
    """
    ネットワークドライブを割り当てる。必要な場合は、Windowsの資格情報の入力画面が出る。
    失敗した場合は pywintypes.error、利用者が待つのをやめた場合は background_wait.Canceled になる。
    """
    resource = win32wnet.NETRESOURCE()
    resource.dwType = win32netcon.RESOURCETYPE_DISK
    resource.lpLocalName = request.letter + ":"
    resource.lpRemoteName = request.remote_path
    flags = win32netcon.CONNECT_UPDATE_PROFILE if request.reconnect else 0
    if not request.use_other_credentials:
        try:
            background_wait.run(_add_connection, resource, flags)
            log.info("mapped %s to %s" % (request.letter, request.remote_path))
            return
        except pywintypes.error as err:
            if not network_resource.is_auth_error(err.winerror):
                raise
    else:
        # 接続できない場所だと資格情報の入力後に長く固まるため、先に別スレッドで届くかどうかを確かめる
        status = network_resource.check_path(request.remote_path)
        if status.is_connection_error():
            raise pywintypes.error(status.error_code, "WNetAddConnection3", status.message)
        flags |= win32netcon.CONNECT_PROMPT
    # 資格情報の入力画面を出すため、メインスレッドで接続する
    # 接続先に届くことは上で確かめているので、長く固まることは少ない
    win32wnet.WNetAddConnection3(hwnd, resource, None, None, flags | win32netcon.CONNECT_INTERACTIVE)
    log.info("mapped %s to %s" % (request.letter, request.remote_path))


def _add_connection(task, resource, flags):
    """(別スレッド)資格情報の入力画面を出さずに接続する。"""
    win32wnet.WNetAddConnection3(0, resource, None, None, flags)


def get_map_error_message(err, request):
    """割り当てに失敗したときに利用者に知らせる文を返す。"""
    if err.winerror == _ERROR_ALREADY_ASSIGNED:
        return _("%(letter)s: ドライブは既に使われています。") % {"letter": request.letter}
    if err.winerror == _ERROR_SESSION_CREDENTIAL_CONFLICT:
        return _("このコンピューターには、既に別のユーザー名で接続しています。同じコンピューターに、複数のユーザー名で同時に接続することはできません。\n接続中のネットワークドライブなどを切断してから、もう一度お試しください。")
    if network_resource.is_connection_error(err.winerror):
        return network_resource.get_connection_error_message(request.remote_path, err.strerror)
    return _("ネットワークドライブを割り当てられませんでした。\n(%(error)s)") % {"error": err.strerror}


def disconnect(letter, force=False):
    """
    ネットワークドライブを切断し、サインイン時の再接続もやめる。DisconnectResult の値を返す。
    失敗した場合は pywintypes.error、利用者が待つのをやめた場合は background_wait.Canceled になる。
    """
    try:
        background_wait.run(_cancel_connection, letter + ":", force)
    except pywintypes.error as err:
        if err.winerror in (_ERROR_OPEN_FILES, _ERROR_DEVICE_IN_USE):
            return DisconnectResult.IN_USE
        if err.winerror == _ERROR_NOT_CONNECTED:
            return DisconnectResult.NOT_CONNECTED
        raise
    log.info("disconnected %s (force=%s)" % (letter, force))
    return DisconnectResult.OK


def _cancel_connection(task, name, force):
    """(別スレッド)接続を切断する。"""
    win32wnet.WNetCancelConnection2(name, win32netcon.CONNECT_UPDATE_PROFILE, force)
