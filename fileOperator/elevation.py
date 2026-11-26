# -*- coding: utf-8 -*-
"""
アクセス拒否になったファイル操作を、管理者権限の falcon に依頼して実行する。

falcon 本体（通常の権限）が名前付きパイプを作り、自分自身を「--fileop <パイプの識別子> <指示のハッシュ>」付きで
管理者権限で起動する。昇格した側はパイプにつないで指示を受け取り、実行した結果とログを同じパイプで返す。

管理者権限で動く処理を、ほかのプログラムに悪用されないよう、次のようにしている。
- 受け渡しは JSON だけを使い、pickle は使わない（読み込んだだけで任意のコードを実行できるため）。
  昇格した側は、操作の種類や値の型が想定どおりかを検証してから実行する
- 一時ファイルは使わない。ユーザーが書き込める場所のファイルを管理者権限で読み書きすると、
  すり替えやシンボリックリンクを使って、別のファイルを読み書きさせられるおそれがあるため。ログも本体に返して記録する
- 指示の SHA-256 をコマンドライン（起動した後は変えられない）で渡し、受け取った指示と照合する
- パイプは推測できない名前で、ほかに同じ名前のものがないことを確かめて作り、1つしか接続できないようにする。
  ネットワーク越しの接続は受け付けない
- 本体は、つないできたのが自分が起動したプロセスかを確かめてから指示を送る
- 昇格した側は、パイプを作ったのが自分と同じプログラム（falcon.exe）かを確かめる。
  また、パイプを作った側に管理者権限のトークンで成りすまされないよう、識別だけを許可してつなぐ
"""
import ctypes
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import struct
import sys
from ctypes import wintypes

import pywintypes
import win32api
import win32con
import win32event
import win32file
import win32pipe
import winerror
from win32com.shell import shell, shellcon

from . import confirmElement, failedElement, past

# 昇格したプロセスに渡す引数。fileop.ARGUMENT と同じ
ARGUMENT = "--fileop"
_PIPE_PREFIX = "\\\\.\\pipe\\falcon_fileop_"
_PIPE_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")
_BUFFER_SIZE = 65536
# 受け取るデータの上限。大量のファイルでも足りる大きさにする
_MAX_MESSAGE_SIZE = 256 * 1024 * 1024
# CreateFile で、つないだ先に識別だけを許可する（成りすましを許さない）
_SECURITY_SQOS_PRESENT = 0x00100000
_SECURITY_IDENTIFICATION = 0x00010000
_PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# 昇格して実行してよい操作と、指示に含めてよいキー
_ALLOWED_OPERATIONS = (
    "past", "delete", "trash", "rename", "changeAttribute", "mkdir", "shortcut", "symbolicLink", "hardLink",
)
_ALLOWED_KEYS = (
    "operation", "files", "target", "from", "to", "to_attrib", "relative", "copy_move_flag", "overwrite",
)

log = logging.getLogger("falcon.elevation")


class ElevationError(Exception):
    """管理者権限での実行に失敗した"""


class ElevationCanceled(ElevationError):
    """UAC の画面で、ユーザーが許可しなかった"""


class ProtocolError(Exception):
    """受け取ったデータが不正"""


# --- 本体（通常の権限）の側 ---------------------------------------------------

def run_elevated(instructions, hwnd=0):
    """
    instructions を管理者権限の falcon で実行し、結果を辞書で返す。
    結果は {"succeeded": int, "failed": [FailedElement], "confirmations": [ConfirmElement]}。
    """
    payload = json.dumps(instructions, ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    pipe_id = secrets.token_hex(16)
    pipe = _create_pipe(_PIPE_PREFIX + pipe_id)
    try:
        process = _start_elevated(pipe_id, digest, hwnd)
        try:
            _connect(pipe, process)
            _verify_client(pipe, process)
            _write_message(pipe, payload, process)
            data = _read_message(pipe, process)
        finally:
            win32api.CloseHandle(process)
    finally:
        win32file.CloseHandle(pipe)
    try:
        result = json.loads(data.decode("utf-8"))
        return _parse_result(result)
    except (ValueError, KeyError, TypeError, ProtocolError) as e:
        raise ElevationError("invalid result: %s" % e)


def _create_pipe(name):
    """名前付きパイプを作る。同じ名前のものがすでにあれば失敗する。"""
    try:
        return win32pipe.CreateNamedPipe(
            name,
            win32pipe.PIPE_ACCESS_DUPLEX | win32pipe.FILE_FLAG_FIRST_PIPE_INSTANCE | win32file.FILE_FLAG_OVERLAPPED,
            win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT | _PIPE_REJECT_REMOTE_CLIENTS,
            1, _BUFFER_SIZE, _BUFFER_SIZE, 0, None)
    except pywintypes.error as e:
        raise ElevationError("cannot create pipe: %s" % e)


def _get_command(pipe_id, digest):
    """管理者権限で起動するプログラムと引数を返す。開発時は falcon.py を実行する。"""
    arguments = "%s %s %s" % (ARGUMENT, pipe_id, digest)
    if hasattr(sys, "frozen"):
        return sys.executable, arguments, os.path.dirname(sys.executable)
    directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return sys.executable, "\"%s\" %s" % (os.path.join(directory, "falcon.py"), arguments), directory


def _start_elevated(pipe_id, digest, hwnd):
    """falcon を管理者権限で起動し、プロセスのハンドルを返す。"""
    program, parameters, directory = _get_command(pipe_id, digest)
    log.debug("elevating: %s %s" % (program, parameters))
    try:
        # SEE_MASK_FLAG_NO_UI: 起動に失敗しても Windows のエラー画面を出さない
        ret = shell.ShellExecuteEx(
            fMask=shellcon.SEE_MASK_NOCLOSEPROCESS | shellcon.SEE_MASK_FLAG_NO_UI,
            hwnd=hwnd,  # UAC の画面を falcon の前面に出すため
            lpVerb="runas",
            lpFile=program,
            lpParameters=parameters,
            lpDirectory=directory,
            nShow=win32con.SW_HIDE,
        )
    except pywintypes.error as e:
        if e.winerror == winerror.ERROR_CANCELLED:
            raise ElevationCanceled()
        raise ElevationError("cannot elevate: %s" % e)
    return ret["hProcess"]


def _wait(overlapped, process):
    """非同期の入出力を待つ。先に相手のプロセスが終わったら失敗にする。"""
    ret = win32event.WaitForMultipleObjects([overlapped.hEvent, process], False, win32event.INFINITE)
    if ret != win32event.WAIT_OBJECT_0:
        raise ElevationError("elevated process exited unexpectedly")


def _connect(pipe, process):
    """昇格したプロセスがつないでくるのを待つ。"""
    overlapped = pywintypes.OVERLAPPED()
    overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
    try:
        ret = win32pipe.ConnectNamedPipe(pipe, overlapped)
        if ret == winerror.ERROR_IO_PENDING:
            try:
                _wait(overlapped, process)
            except ElevationError:
                win32file.CancelIo(pipe)
                raise
            win32file.GetOverlappedResult(pipe, overlapped, False)
        # ERROR_PIPE_CONNECTED は、待つ前にもうつながっていたことを表す
    except pywintypes.error as e:
        raise ElevationError("cannot connect: %s" % e)
    finally:
        win32api.CloseHandle(overlapped.hEvent)


def _verify_client(pipe, process):
    """つないできたのが、自分で起動したプロセスかを確かめる。"""
    client = win32pipe.GetNamedPipeClientProcessId(pipe)
    launched = _get_process_id(process)
    if client == launched:
        return
    # 開発時は、仮想環境の python.exe が本来の python.exe を子プロセスとして起動するので、親子関係も認める
    if not hasattr(sys, "frozen") and _get_parent_process_id(client) == launched:
        return
    raise ElevationError("unexpected client process %d (launched %d)" % (client, launched))


def _get_process_id(process):
    """プロセスのハンドルから ID を得る。"""
    return ctypes.windll.kernel32.GetProcessId(int(process))


def _get_parent_process_id(pid):
    """プロセスの親の ID を返す。わからなければ None。"""
    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_wchar * 260),
        ]
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
    if snapshot in (None, wintypes.HANDLE(-1).value):
        return None
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = kernel32.Process32FirstW(wintypes.HANDLE(snapshot), ctypes.byref(entry))
        while ok:
            if entry.th32ProcessID == pid:
                return entry.th32ParentProcessID
            ok = kernel32.Process32NextW(wintypes.HANDLE(snapshot), ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(wintypes.HANDLE(snapshot))
    return None


def _write_message(pipe, data, process):
    """長さを先頭に付けて送る。"""
    overlapped = pywintypes.OVERLAPPED()
    overlapped.hEvent = win32event.CreateEvent(None, True, False, None)
    try:
        message = struct.pack("<I", len(data)) + data
        while message:
            win32file.WriteFile(pipe, message, overlapped)
            _wait(overlapped, process)
            written = win32file.GetOverlappedResult(pipe, overlapped, False)
            message = message[written:]
    except pywintypes.error as e:
        raise ElevationError("cannot write: %s" % e)
    finally:
        win32api.CloseHandle(overlapped.hEvent)


def _read_message(pipe, process):
    """長さが先頭に付いたデータを受け取る。"""
    overlapped = pywintypes.OVERLAPPED()
    overlapped.hEvent = win32event.CreateEvent(None, True, False, None)

    def read(size):
        data = b""
        while len(data) < size:
            dummy, buffer = win32file.ReadFile(pipe, min(size - len(data), _BUFFER_SIZE), overlapped)
            _wait(overlapped, process)
            count = win32file.GetOverlappedResult(pipe, overlapped, False)
            data += bytes(buffer[:count])
        return data

    try:
        size = struct.unpack("<I", read(4))[0]
        if size > _MAX_MESSAGE_SIZE:
            raise ElevationError("message too large")
        return read(size)
    except pywintypes.error as e:
        # 昇格した側が結果を返す前に終わった場合も、ここに来る
        raise ElevationError("cannot read: %s" % e)
    finally:
        win32api.CloseHandle(overlapped.hEvent)


def _parse_result(result):
    """昇格した側から返された結果を、失敗・確認の項目のオブジェクトに戻す。ログは本体のログに記録する。"""
    if not isinstance(result, dict):
        raise ProtocolError("result is not an object")
    for level, name, message in _expect_list(result.get("logs", [])):
        logging.getLogger(str(name)).log(int(level), "[elevated] %s" % message)
    if result.get("error"):
        raise ElevationError("elevated process failed: %s" % result["error"])
    succeeded = result.get("succeeded", 0)
    if not isinstance(succeeded, int):
        raise ProtocolError("succeeded is not an int")
    failed = []
    for elem in _expect_list(result.get("failed", [])):
        failed.append(failedElement.FailedElement(_to_tuple(elem["elem"]), _to_tuple(elem["msg"])))
    confirmations = []
    for elem in _expect_list(result.get("confirmations", [])):
        # past.Element() はファイルを調べるので、調べた結果をそのまま入れる
        item = past.Element.__new__(past.Element)
        item.path = str(elem["path"])
        item.destpath = str(elem["destpath"])
        item.isfile = bool(elem["isfile"])
        item.size = int(elem["size"])
        item.is_link = bool(elem["is_link"])
        confirmations.append(confirmElement.ConfirmElement(item, int(elem["msg_number"]), str(elem["msg_string"])))
    return {"succeeded": succeeded, "failed": failed, "confirmations": confirmations}


# --- 昇格した側 ---------------------------------------------------------------

def serve(pipe_id, digest, execute):
    """
    本体から指示を受け取り、execute(instructions) で実行して結果を返す。
    execute は FileOperator の output を返す関数。ログは logs に集めて本体に返す。
    """
    if not _PIPE_ID_PATTERN.fullmatch(pipe_id) or not _DIGEST_PATTERN.fullmatch(digest):
        raise ProtocolError("invalid arguments")
    handler = _MemoryHandler()
    logging.getLogger("falcon").addHandler(handler)
    pipe = _open_pipe(_PIPE_PREFIX + pipe_id)
    try:
        _verify_server(pipe)
        try:
            payload = _read_blocking(pipe)
            if not hmac.compare_digest(hashlib.sha256(payload).hexdigest(), digest):
                raise ProtocolError("digest mismatch")
            instructions = validate_instructions(json.loads(payload.decode("utf-8")))
            output = execute(instructions)
            result = _make_result(output)
            result["logs"] = handler.records
            data = json.dumps(result, ensure_ascii=False).encode("utf-8")
        except Exception as e:
            log.exception("elevated operation failed")
            result = {"error": "%s: %s" % (type(e).__name__, e), "logs": handler.records}
            data = json.dumps(result, ensure_ascii=False, default=str).encode("utf-8")
        _write_blocking(pipe, data)
    finally:
        win32file.CloseHandle(pipe)


class _MemoryHandler(logging.Handler):
    """ログを本体に返すため、メモリにためておく。管理者権限ではファイルに書かない。"""

    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records = []

    def emit(self, record):
        try:
            self.records.append([record.levelno, record.name, record.getMessage()])
        except Exception:
            self.handleError(record)


def _open_pipe(name):
    """本体のパイプにつなぐ。つないだ先には、識別だけを許可する。"""
    try:
        return win32file.CreateFile(
            name, win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None, win32file.OPEN_EXISTING,
            _SECURITY_SQOS_PRESENT | _SECURITY_IDENTIFICATION, None)
    except pywintypes.error as e:
        raise ProtocolError("cannot open pipe: %s" % e)


def _verify_server(pipe):
    """パイプを作ったのが、自分と同じプログラムかを確かめる。"""
    server = win32pipe.GetNamedPipeServerProcessId(pipe)
    server_image = _get_process_image(server)
    own_image = _get_process_image(os.getpid())
    if server_image is None or own_image is None or os.path.normcase(server_image) != os.path.normcase(own_image):
        raise ProtocolError("unexpected server process: %s" % server_image)


def _get_process_image(pid):
    """プロセスの exe の完全なパスを返す。わからなければ None。"""
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.restype = wintypes.HANDLE
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(wintypes.HANDLE(handle), 0, buffer, ctypes.byref(size)):
            return None
        return buffer.value
    finally:
        kernel32.CloseHandle(wintypes.HANDLE(handle))


def _read_blocking(pipe):
    """長さが先頭に付いたデータを受け取る。"""
    def read(size):
        data = b""
        while len(data) < size:
            dummy, chunk = win32file.ReadFile(pipe, min(size - len(data), _BUFFER_SIZE))
            if not chunk:
                raise ProtocolError("pipe closed")
            data += chunk
        return data
    size = struct.unpack("<I", read(4))[0]
    if size > _MAX_MESSAGE_SIZE:
        raise ProtocolError("message too large")
    return read(size)


def _write_blocking(pipe, data):
    """長さを先頭に付けて送る。"""
    win32file.WriteFile(pipe, struct.pack("<I", len(data)) + data)


def validate_instructions(instructions):
    """受け取った指示が、想定した形かを確かめる。リストの中のリストは、元のタプルに戻す。"""
    if not isinstance(instructions, dict):
        raise ProtocolError("instructions is not an object")
    if instructions.get("operation") not in _ALLOWED_OPERATIONS:
        raise ProtocolError("operation not allowed: %r" % instructions.get("operation"))
    result = {}
    for key, value in instructions.items():
        if key not in _ALLOWED_KEYS:
            raise ProtocolError("key not allowed: %r" % key)
        if isinstance(value, list):
            value = [_to_tuple(_check_value(item, nested=True)) for item in value]
        else:
            _check_value(value)
        result[key] = value
    return result


def _check_value(value, nested=False):
    """値が、文字列・数値・真偽値・None か、それらのリスト（1段まで）かを確かめる。"""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if nested and isinstance(value, list) and all(v is None or isinstance(v, (str, bool, int)) for v in value):
        return value
    raise ProtocolError("unexpected value: %r" % (value,))


def _make_result(output):
    """FileOperator の output から、本体に返す結果を作る。"""
    failed = [{"elem": elem.elem, "msg": elem.msg} for elem in output["failed"]]
    confirmations = []
    for confirmation in output["need_to_confirm"].Iterate():
        elem = confirmation.elem
        confirmations.append({
            "path": elem.path, "destpath": elem.destpath, "isfile": elem.isfile, "size": elem.size,
            "is_link": elem.is_link, "msg_number": confirmation.msg_number, "msg_string": confirmation.msg_string,
        })
    return {"succeeded": output["succeeded"], "failed": failed, "confirmations": confirmations}


# --- 共通 ---------------------------------------------------------------------

def _expect_list(value):
    if not isinstance(value, list):
        raise ProtocolError("list expected")
    return value


def _to_tuple(value):
    """JSON でリストになったタプルを、タプルに戻す。"""
    return tuple(value) if isinstance(value, list) else value
