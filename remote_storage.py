# -*- coding: utf-8 -*-
# Falcon remote storage (FTP / FTPS / SFTP)
# Note: All comments except these top lines will be written in Japanese.

"""
FTP・FTPS・SFTP のサーバーに接続し、フォルダの一覧の取得、ファイルの転送（ダウンロード・アップロード）、
フォルダの作成、削除、名前の変更、パーミッションの変更を行う処理です。

場所は「ftp://ユーザー名@サーバー:ポート/パス」の形の URL で表します。
- ftp: 暗号化しない FTP
- ftps: TLS で暗号化する FTP。接続後に暗号化を始める方式（Explicit FTPS、AUTH TLS）。
  ポート番号が 990 の場合は、接続した直後から暗号化する方式（Implicit FTPS）
- sftp: SSH の SFTP

FTPS で検証できない証明書（自分で作った証明書など）は、利用者が指紋を確かめて許可した証明書だけを使います（ピン留め）。
許可した証明書と違う証明書が出てきた場合は、接続しません。
プロキシを使う設定の場合は、HTTP プロキシの CONNECT で接続します（FTP のデータ用の接続も同じ）。

この中の関数は別スレッドから呼ばれます。画面の部品には触りません。
認証の入力やホスト鍵の確認が必要なときは、例外（AuthRequired など）で呼び出し側に知らせます。
画面を使う処理は remote_connect.py にあります。
"""

import base64
import datetime
import ftplib
import hashlib
import io
import json
import logging
import os
import posixpath
import re
import socket
import ssl
import stat
import threading
import warnings

import pywintypes
import win32cred

log = logging.getLogger("falcon.remote_storage")

SCHEME_FTP = "ftp"
SCHEME_FTPS = "ftps"
SCHEME_SFTP = "sftp"
SCHEMES = (SCHEME_FTP, SCHEME_FTPS, SCHEME_SFTP)
_DEFAULT_PORTS = {SCHEME_FTP: 21, SCHEME_FTPS: 21, SCHEME_SFTP: 22}

# 接続・応答を待つ秒数
_TIMEOUT = 30
# ダウンロードで一度に読む大きさ
_BLOCK_SIZE = 64 * 1024
# SFTP で一度に要求する大きさと、まとめて要求する範囲
_SFTP_CHUNK = 32 * 1024
_SFTP_WINDOW = 4 * 1024 * 1024
# 資格情報マネージャーに保存するときの名前の先頭
_CREDENTIAL_PREFIX = "falcon:"
# falcon が確認したSFTPサーバーのホスト鍵を保存するファイル
KNOWN_HOSTS_FILE_NAME = "known_hosts"
# 利用者が許可した、検証できない FTPS の証明書の指紋を保存するファイル
TRUSTED_CERTIFICATES_FILE_NAME = "trusted_certificates.json"
# このポート番号の ftps は、接続した直後から暗号化する方式（Implicit FTPS）にする
IMPLICIT_FTPS_PORT = 990


class RemoteError(Exception):
    """接続や操作に失敗した。メッセージは利用者に見せる文章。"""


class ConnectError(RemoteError):
    """サーバーに接続できない"""


class AuthRequired(RemoteError):
    """ユーザー名とパスワードが必要、または違っている"""


class UnknownHostKey(RemoteError):
    """SFTPサーバーのホスト鍵が、まだ確認されていない"""

    def __init__(self, message, host_key_name, key):
        super().__init__(message)
        self.host_key_name = host_key_name
        self.key = key

    def get_fingerprint(self):
        """鍵の指紋（SHA256）を ssh と同じ形で返す"""
        digest = hashlib.sha256(self.key.asbytes()).digest()
        return "%s SHA256:%s" % (self.key.get_name(), base64.b64encode(digest).decode("ascii").rstrip("="))


class UntrustedCertificate(RemoteError):
    """
    FTPSサーバーの証明書を検証できない、または以前に許可した証明書と違う。
    fingerprint は証明書の指紋（SHA256）、details は発行先・発行者・有効期限などの説明。
    changed が True の場合は、以前に許可した証明書と違う（なりすましの可能性がある）。
    """

    def __init__(self, message, fingerprint="", details="", changed=False):
        super().__init__(message)
        self.fingerprint = fingerprint
        self.details = details
        self.changed = changed


class Canceled(Exception):
    """利用者が中止した"""


class Location:
    """サーバー上の場所"""

    def __init__(self, scheme, host, port=None, user="", path=""):
        self.scheme = scheme
        self.host = host
        self.port = port or _DEFAULT_PORTS[scheme]
        self.user = user
        # サーバー上の絶対パス（/ から始まる）。空文字列の場合は、ログインしたときのフォルダ
        self.path = path

    def get_server_key(self):
        """同じサーバーへの接続を見分けるための文字列"""
        return "%s://%s:%d" % (self.scheme, self.host.lower(), self.port)

    def get_url(self, path=None, with_user=True):
        """URL を返す。path を指定した場合は、そのパスの URL を返す"""
        path = self.path if path is None else path
        host = "[%s]" % self.host if ":" in self.host else self.host
        if self.port != _DEFAULT_PORTS[self.scheme]:
            host += ":%d" % self.port
        if with_user and self.user:
            host = "%s@%s" % (self.user, host)
        return "%s://%s%s" % (self.scheme, host, path)

    def child(self, path):
        """同じサーバーの別のパスの Location を返す"""
        return Location(self.scheme, self.host, self.port, self.user, path)

    def get_display_host(self):
        """読み上げや表示に使う、サーバーの名前"""
        return self.host if self.port == _DEFAULT_PORTS[self.scheme] else "%s:%d" % (self.host, self.port)


class Entry:
    """フォルダの中の1つの項目"""

    def __init__(self, name, is_dir, size=-1, modified=None, permissions=None, precision=1, is_link=False):
        self.name = name
        self.is_dir = is_dir
        # シンボリックリンクかどうか。is_dir はリンク先がフォルダかどうかを表す
        self.is_link = is_link
        self.size = size
        # 更新日時（タイムゾーン付きの datetime）。わからない場合は None
        self.modified = modified
        # UNIX のパーミッション（0o755 など）。わからない場合は None
        self.permissions = permissions
        # 更新日時の精度（秒）。FTP の LIST では分や日までしかわからない
        self.precision = precision


class Credentials:
    """接続に使う資格情報"""

    def __init__(self, user="", password="", key_file=""):
        self.user = user
        # パスワード。鍵ファイルを使う場合は鍵のパスフレーズとしても使う。わからない場合は None
        self.password = password
        # SFTP で使う秘密鍵のファイル。使わない場合は空文字列
        self.key_file = key_file


def is_remote_url(text):
    """FTP・FTPS・SFTP の URL かどうかを返す"""
    if not isinstance(text, str):
        return False
    lower = text.lower()
    return any(lower.startswith(scheme + "://") for scheme in SCHEMES)


def parse_url(text):
    """
    URL を Location にする。正しくない場合は ValueError（メッセージは利用者に見せる文章）。
    ファイル名に使われる # や ? をそのまま扱うため、urllib は使わずに分ける。
    """
    text = text.strip()
    if not is_remote_url(text):
        raise ValueError(_("ftp://、ftps://、sftp:// のいずれかで始まる URL を入力してください。"))
    scheme, rest = text.split("://", 1)
    scheme = scheme.lower()
    rest = rest.replace("\\", "/")
    slash = rest.find("/")
    if slash < 0:
        authority, path = rest, ""
    else:
        authority, path = rest[:slash], rest[slash:]
    user = ""
    if "@" in authority:
        user, authority = authority.rsplit("@", 1)
        # パスワードを URL に含めることはできない（履歴や設定にパスワードが残るため）
        if ":" in user:
            raise ValueError(_("URL にパスワードを含めることはできません。パスワードは接続するときに入力してください。"))
    port = None
    if authority.startswith("["):
        end = authority.find("]")
        if end < 0:
            raise ValueError(_("サーバーの名前が正しくありません。"))
        host, port_text = authority[1:end], authority[end + 1:]
        if port_text:
            if not port_text.startswith(":"):
                raise ValueError(_("サーバーの名前が正しくありません。"))
            port_text = port_text[1:]
    elif ":" in authority:
        host, port_text = authority.rsplit(":", 1)
    else:
        host, port_text = authority, ""
    if port_text:
        if not port_text.isdigit() or not 0 < int(port_text) < 65536:
            raise ValueError(_("ポート番号が正しくありません。"))
        port = int(port_text)
    if host == "" or re.search(r"[\s/\\@]", host):
        raise ValueError(_("サーバーの名前が正しくありません。"))
    return Location(scheme, host, port, user, normalize_path(path) if path else "")


def normalize_path(path):
    """サーバー上のパスを / から始まり、末尾に / を付けない形にする"""
    path = posixpath.normpath("/" + path.lstrip("/"))
    # normpath は先頭の // を残すことがある
    return "/" + path.lstrip("/")


def get_parent_path(path):
    """親フォルダのパスを返す。ルートの場合は None"""
    if path in ("", "/"):
        return None
    return posixpath.dirname(path)


def join_path(directory, name):
    """フォルダのパスと名前をつなげる"""
    return posixpath.join(directory, name)


def get_name(path):
    """パスの最後の名前を返す"""
    return path.rstrip("/").rsplit("/", 1)[-1]


def validate_name(name):
    """サーバー上のファイル・フォルダの名前として使えるかどうかを調べ、使えなければ理由を返す。使えれば空文字列"""
    if name.strip() == "":
        return _("名前を入力してください。")
    if "/" in name or "\\" in name or "\0" in name:
        return _("名前に / や \\ は使えません。")
    if name in (".", ".."):
        return _("この名前は使えません。")
    return ""


def is_same_server(a, b):
    """2つの Location が、同じサーバーに同じユーザーで接続するものかどうかを返す"""
    return a.get_server_key() == b.get_server_key() and a.user == b.user


def format_permissions(mode):
    """パーミッションを rwxr-xr-x (755) の形の文字列にする"""
    if mode is None:
        return ""
    text = ""
    for shift in (6, 3, 0):
        bits = (mode >> shift) & 7
        text += ("r" if bits & 4 else "-") + ("w" if bits & 2 else "-") + ("x" if bits & 1 else "-")
    return "%s (%03o)" % (text, mode & 0o777)


def _parse_permission_string(text):
    """LIST の rwxr-xr-x の部分をパーミッションの数値にする。わからなければ None"""
    if len(text) < 9:
        return None
    mode = 0
    for index, char in enumerate(text[:9]):
        if char not in "-rwxsStT":
            return None
        if char != "-" and char not in "ST":
            mode |= 1 << (8 - index)
    return mode


# ---- 資格情報 ----

class CredentialStore:
    """
    資格情報の保管場所。
    falcon を終了するまでの間はメモリに持ち、保存を指定された場合は Windows の資格情報マネージャーにも保存する。
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._memory = {}
        # サーバーの key -> SFTP の鍵ファイルのパス。秘密の情報ではないので falcon の設定に保存する（remote_connect）
        self._key_files = {}

    def get(self, location):
        """
        保存されている資格情報を返す。なければ None。URL のユーザー名と違うものは返さない。
        パスワードがなくても鍵ファイルが指定されていれば、鍵ファイルだけの資格情報を返す。
        """
        key = location.get_server_key()
        with self._lock:
            credentials = self._memory.get(key)
            key_file = self._key_files.get(key, "")
        if credentials is None:
            credentials = self._read_windows(key)
        if credentials is not None and location.user and credentials.user != location.user:
            credentials = None
        if credentials is None:
            if not key_file or not location.user:
                return None
            return Credentials(location.user, None, key_file)
        return Credentials(credentials.user, credentials.password, credentials.key_file or key_file)

    def set_key_files(self, key_files):
        """鍵ファイルの一覧（サーバーの key -> パス）を入れ替える"""
        with self._lock:
            self._key_files = dict(key_files)

    def get_key_file(self, location):
        with self._lock:
            return self._key_files.get(location.get_server_key(), "")

    def remember(self, location, credentials, save=False):
        """資格情報を覚える。save=True なら資格情報マネージャーにも保存する"""
        key = location.get_server_key()
        with self._lock:
            self._memory[key] = credentials
        if save:
            try:
                win32cred.CredWrite({
                    "Type": win32cred.CRED_TYPE_GENERIC,
                    "TargetName": _CREDENTIAL_PREFIX + key,
                    "UserName": credentials.user,
                    "CredentialBlob": credentials.password or "",
                    "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE,
                }, 0)
            except pywintypes.error as err:
                log.warning("Cannot save the credentials of %s: %s" % (key, err))

    def forget(self, location):
        """覚えている資格情報を消す（パスワードが違っていたときに使う）"""
        key = location.get_server_key()
        with self._lock:
            self._memory.pop(key, None)
        try:
            win32cred.CredDelete(_CREDENTIAL_PREFIX + key, win32cred.CRED_TYPE_GENERIC, 0)
        except pywintypes.error:
            pass  # 保存されていない

    def _read_windows(self, key):
        try:
            credential = win32cred.CredRead(_CREDENTIAL_PREFIX + key, win32cred.CRED_TYPE_GENERIC, 0)
        except pywintypes.error:
            return None
        blob = credential.get("CredentialBlob") or b""
        password = blob.decode("utf-16-le") if isinstance(blob, bytes) else str(blob)
        return Credentials(credential.get("UserName") or "", password)


credential_store = CredentialStore()


class TrustStore:
    """
    利用者が接続を許可した、検証できない FTPS の証明書の指紋（サーバーの key -> SHA256）。
    trusted_certificates.json（設定ファイルと同じ場所）に保存する。保存できない場合も、falcon を終了するまでは使う。
    """

    def __init__(self, path=None):
        self._lock = threading.Lock()
        self._path = path
        self._pins = None

    def _load(self):
        """(ロックを持って呼ぶ)ファイルから読む"""
        if self._pins is not None:
            return
        self._pins = {}
        path = self._get_path()
        if not os.path.isfile(path):
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._pins = {str(k): str(v) for k, v in data.items()}
        except (OSError, ValueError) as err:
            log.warning("Cannot load %s: %s" % (path, err))

    def _get_path(self):
        return self._path or os.path.abspath(TRUSTED_CERTIFICATES_FILE_NAME)

    def get_pin(self, location):
        """許可した証明書の指紋を返す。なければ None"""
        with self._lock:
            self._load()
            return self._pins.get(location.get_server_key())

    def trust(self, location, fingerprint):
        """証明書を許可して保存する"""
        with self._lock:
            self._load()
            self._pins[location.get_server_key()] = fingerprint
            pins = dict(self._pins)
        path = self._get_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(pins, f, ensure_ascii=False, indent=1)
        except OSError as err:
            log.warning("Cannot save %s: %s" % (path, err))


certificate_trust = TrustStore()


def get_certificate_fingerprint(der):
    """証明書（DER）の指紋を、SHA256:xx:xx:… の形で返す"""
    digest = hashlib.sha256(der).hexdigest().upper()
    return "SHA256:" + ":".join(digest[i:i + 2] for i in range(0, len(digest), 2))


def describe_certificate(der):
    """証明書の発行先・発行者・有効期限を、利用者に見せる文章にする。読めなければ空文字列"""
    try:
        from cryptography import x509
        cert = x509.load_der_x509_certificate(der)
        return _("発行先: %(subject)s\n発行者: %(issuer)s\n有効期限: %(start)s から %(end)s まで") % {
            "subject": cert.subject.rfc4514_string(), "issuer": cert.issuer.rfc4514_string(),
            "start": cert.not_valid_before_utc.strftime("%Y-%m-%d"), "end": cert.not_valid_after_utc.strftime("%Y-%m-%d")}
    except Exception as err:
        log.debug("Cannot describe the certificate: %s" % err)
        return ""


# ---- プロキシ ----

_proxy = None
_proxy_lock = threading.Lock()


def set_proxy(proxy):
    """FTP・SFTP の接続に使う HTTP プロキシ (サーバー, ポート) を設定する。None なら直接接続する"""
    global _proxy
    with _proxy_lock:
        _proxy = proxy


def get_proxy():
    with _proxy_lock:
        return _proxy


def open_socket(host, port, timeout):
    """
    サーバーへの TCP の接続を開く。プロキシを使う設定なら、HTTP プロキシの CONNECT で中継してもらう。
    失敗した場合は OSError になる。
    """
    proxy = get_proxy()
    if proxy is None:
        return socket.create_connection((host, port), timeout)
    sock = socket.create_connection(proxy, timeout)
    try:
        target = "[%s]:%d" % (host, port) if ":" in host else "%s:%d" % (host, port)
        sock.sendall(("CONNECT %s HTTP/1.1\r\nHost: %s\r\n\r\n" % (target, target)).encode("ascii"))
        response = b""
        while b"\r\n\r\n" not in response:
            data = sock.recv(4096)
            if not data:
                raise ConnectionError(_("プロキシサーバーが接続を閉じました。"))
            response += data
            if len(response) > 65536:
                raise ConnectionError(_("プロキシサーバーの応答が正しくありません。"))
        status = response.split(b"\r\n", 1)[0].decode("latin-1")
        parts = status.split(" ", 2)
        if len(parts) < 2 or parts[1] != "200":
            raise ConnectionError(_("プロキシサーバーが中継を断りました。(%(status)s)") % {"status": status})
        # CONNECT の応答の後に、サーバーからのデータが続いて届いていることはない（サーバーはまだ何も送っていない）
        return sock
    except BaseException:
        sock.close()
        raise


def get_known_hosts_path():
    """falcon が確認したホスト鍵を保存するファイルのパス"""
    return os.path.abspath(KNOWN_HOSTS_FILE_NAME)


def _import_paramiko():
    """paramiko を読み込む。読み込みに時間がかかるため、SFTP を使うときだけ読み込む"""
    # 32bit の Python では遅いという警告が出るが、利用者には関係ないので出さない
    warnings.filterwarnings("ignore", message=".*32-bit Python.*")
    import paramiko
    return paramiko


# 利用者が確認したホスト鍵。ファイルに保存できなかった場合も、falcon を終了するまでは使う
_accepted_host_keys = []
_accepted_host_keys_lock = threading.Lock()


def add_known_host(error):
    """利用者が確認したホスト鍵を覚えて、ファイルに保存する。error は UnknownHostKey"""
    with _accepted_host_keys_lock:
        _accepted_host_keys.append((error.host_key_name, error.key))
    paramiko = _import_paramiko()
    path = get_known_hosts_path()
    keys = paramiko.HostKeys()
    try:
        if os.path.isfile(path):
            keys.load(path)
        keys.add(error.host_key_name, error.key.get_name(), error.key)
        keys.save(path)
    except (OSError, paramiko.SSHException) as err:
        log.warning("Cannot save the host key to %s: %s" % (path, err))


# ---- 接続 ----

class Client:
    """サーバーへの1つの接続。同時に複数のスレッドから使わないこと"""

    def __init__(self, location):
        self.location = location

    def get_initial_path(self):
        """ログインしたときのフォルダの絶対パスを返す"""
        raise NotImplementedError

    def list_dir(self, path):
        """フォルダの中身を Entry のリストで返す"""
        raise NotImplementedError

    def get_entry(self, path):
        """パスの項目を Entry で返す。見つからなければ RemoteError"""
        raise NotImplementedError

    def download(self, path, local_path, on_progress=None, offset=0):
        """
        ファイルをダウンロードする。on_progress(今回読んだバイト数) を呼ぶ。
        offset を指定した場合は、その位置から読み、ローカルのファイルの末尾に書き足す（続きからの転送）。
        on_progress が Canceled を投げると中止する。offset が 0 の場合は、途中まで書いたファイルを消す。
        """
        raise NotImplementedError

    def upload(self, local_path, path, on_progress=None, offset=0):
        """
        ファイルをアップロードする。on_progress(今回送ったバイト数) を呼ぶ。
        offset を指定した場合は、ローカルのファイルのその位置から送り、サーバーのファイルの末尾に書き足す。
        on_progress が Canceled を投げると中止する。
        """
        raise NotImplementedError

    def create_file(self, path):
        """空のファイルを作る"""
        raise NotImplementedError

    def make_dir(self, path):
        """フォルダを作る"""
        raise NotImplementedError

    def remove_file(self, path):
        """ファイルを削除する"""
        raise NotImplementedError

    def remove_dir(self, path):
        """空のフォルダを削除する"""
        raise NotImplementedError

    def rename(self, old_path, new_path):
        """名前を変える（同じサーバーの中で移動する）"""
        raise NotImplementedError

    def chmod(self, path, mode):
        """パーミッションを変える"""
        raise NotImplementedError

    def set_modified(self, path, modified):
        """更新日時を変える。サーバーが対応していない場合は何もしない。変えられたら True を返す"""
        raise NotImplementedError

    def check_alive(self):
        """接続が使えるかを確かめる。切れていれば ConnectError"""
        raise NotImplementedError

    def get_real_path(self, path):
        """シンボリックリンクをたどった実際のパスを返す。調べられない場合は None"""
        return None

    def make_dirs(self, path):
        """途中のフォルダも含めて、フォルダを作る。既にある場合は何もしない"""
        try:
            entry = self.get_entry(path)
        except ConnectError:
            raise
        except RemoteError:
            entry = None
        if entry is not None:
            if not entry.is_dir:
                raise RemoteError(_("同じ名前のファイルがあるため、フォルダを作れません。"))
            return
        parent = get_parent_path(path)
        if parent is not None and parent != path:
            self.make_dirs(parent)
        self.make_dir(path)

    def close(self):
        raise NotImplementedError


def connect(location, credentials):
    """
    サーバーに接続してログインした Client を返す。credentials が None の場合は、匿名や SSH の鍵で接続を試みる。
    失敗した場合は RemoteError の派生クラスになる。
    """
    if location.scheme == SCHEME_SFTP:
        return _SftpClient(location, credentials)
    return _FtpClient(location, credentials)


def _connection_error_message(location, err):
    return _("%(host)s に接続できませんでした。\nサーバーの名前とポート番号、ネットワークの接続を確認してください。\n(%(error)s)") % {
        "host": location.get_display_host(), "error": _describe(err)}


def _describe(err):
    """例外を、利用者に見せる短い文章にする"""
    if isinstance(err, socket.timeout):
        return _("応答がありません")
    if isinstance(err, socket.gaierror):
        return _("サーバーが見つかりません")
    if isinstance(err, OSError) and err.strerror:
        return err.strerror
    return str(err) or err.__class__.__name__


# ---- FTP / FTPS ----

# LIST の結果（UNIX の ls -l 形式）
_UNIX_LIST = re.compile(
    r"^(?P<type>[\-dlbcps])(?P<perms>\S*)\s+\d+\s+\S+\s+\S+\s+(?P<size>\d+)\s+"
    r"(?P<month>[A-Za-z]{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{1,2}:\d{2}|\d{4})\s(?P<name>.+)$")
# LIST の結果（Windows の IIS の形式）
_DOS_LIST = re.compile(
    r"^(?P<date>\d{2}-\d{2}-\d{2,4})\s+(?P<time>\d{1,2}:\d{2}[AaPp][Mm])\s+(?P<size><DIR>|\d+)\s+(?P<name>.+)$")
_MONTHS = {name: index + 1 for index, name in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"))}


class _CertificateChanged(Exception):
    """(内部用)許可した証明書と違う証明書が出てきた。der は出てきた証明書"""

    def __init__(self, der):
        super().__init__("certificate changed")
        self.der = der


class _ConnectionMixin:
    """
    ftplib の FTP・FTP_TLS に足す処理。
    - 接続は open_socket で開く（プロキシに対応するため）
    - データ用の接続はパッシブだけにして、サーバーが返すアドレスではなく制御用の接続と同じサーバーに接続する
    - 接続した直後から暗号化する方式（Implicit FTPS）に対応する
    - ピン留めした証明書と同じかを確かめる
    """

    _implicit = False
    _pin = None

    def connect(self, host="", port=0, timeout=-999, source_address=None):
        self.host = host
        self.port = port
        self.sock = open_socket(host, port, self.timeout)
        self.af = self.sock.family
        if self._implicit:
            self.sock = self.context.wrap_socket(self.sock, server_hostname=host)
            self._check_pin(self.sock)
        self.file = self.sock.makefile("r", encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome

    def _check_pin(self, sock):
        """ピン留めした証明書と違えば _CertificateChanged を投げる"""
        if self._pin is None:
            return
        der = sock.getpeercert(binary_form=True) or b""
        if get_certificate_fingerprint(der) != self._pin:
            raise _CertificateChanged(der)

    def makepasv(self):
        """
        パッシブのデータ用の接続先を返す。サーバーが返すアドレスは使わず、制御用の接続と同じサーバーにする。
        プロキシを使う場合は、プロキシのアドレスではなくサーバーの名前にする。
        """
        if self.af == socket.AF_INET:
            dummy, port = ftplib.parse227(self.sendcmd("PASV"))
        else:
            dummy, port = ftplib.parse229(self.sendcmd("EPSV"), self.sock.getpeername())
        if get_proxy() is not None:
            return self.host, port
        return self.sock.getpeername()[0], port

    def ntransfercmd(self, cmd, rest=None):
        host, port = self.makepasv()
        conn = open_socket(host, port, self.timeout)
        try:
            if rest is not None:
                self.sendcmd("REST %s" % rest)
            resp = self.sendcmd(cmd)
            # 2xx が先に返るサーバーがある
            if resp[0] == "2":
                resp = self.getresp()
            if resp[0] != "1":
                raise ftplib.error_reply(resp)
        except BaseException:
            conn.close()
            raise
        size = ftplib.parse150(resp) if resp[:3] == "150" else None
        return conn, size


class _Ftp(_ConnectionMixin, ftplib.FTP):
    """暗号化しない FTP"""


class _FtpTls(_ConnectionMixin, ftplib.FTP_TLS):
    """FTPS"""

    def __init__(self, implicit, pin, **kwargs):
        super().__init__(**kwargs)
        self._implicit = implicit
        self._pin = pin

    def auth(self):
        resp = super().auth()
        self._check_pin(self.sock)
        return resp

    def ntransfercmd(self, cmd, rest=None):
        conn, size = _ConnectionMixin.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            try:
                # vsftpd や FileZilla Server は、データ用の接続で制御用の接続の TLS セッションを再利用することを求める。
                # ftplib はこれに対応していないので、ここで再利用する
                conn = self.context.wrap_socket(conn, server_hostname=self.host, session=self.sock.session)
                self._check_pin(conn)
            except BaseException:
                conn.close()
                raise
        return conn, size


class _FtpClient(Client):
    """FTP・FTPS の接続"""

    def __init__(self, location, credentials):
        super().__init__(location)
        self._mlsd_supported = True
        self._implicit = location.scheme == SCHEME_FTPS and location.port == IMPLICIT_FTPS_PORT
        self._pin = certificate_trust.get_pin(location) if location.scheme == SCHEME_FTPS else None
        self._ftp = self._open(credentials)

    def _make_context(self, verify=True):
        context = ssl.create_default_context()
        if self._pin is not None or not verify:
            # 証明書の検証の代わりに、利用者が許可した証明書と同じかを確かめる（_ConnectionMixin._check_pin）
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    def _untrusted(self, err):
        """検証できない証明書を取り出して、指紋を付けた UntrustedCertificate を作る"""
        der = self._fetch_certificate()
        return UntrustedCertificate(
            _("%(host)s の証明書を確認できませんでした。\n(%(error)s)") % {
                "host": self.location.get_display_host(), "error": err.verify_message or err},
            get_certificate_fingerprint(der) if der else "", describe_certificate(der) if der else "")

    def _changed(self, err):
        return UntrustedCertificate(
            _("%(host)s の証明書が、以前に許可したものと違います。\nなりすましの可能性があります。") % {
                "host": self.location.get_display_host()},
            get_certificate_fingerprint(err.der), describe_certificate(err.der), changed=True)

    def _fetch_certificate(self):
        """検証せずに接続して、サーバーの証明書（DER）を取り出す。取り出せなければ None"""
        location = self.location
        ftp = _FtpTls(self._implicit, None, context=self._make_context(verify=False), timeout=_TIMEOUT, encoding="utf-8")
        try:
            ftp.connect(location.host, location.port)
            if not self._implicit:
                ftp.auth()
            return ftp.sock.getpeercert(binary_form=True)
        except (OSError, EOFError, ftplib.Error) as err:
            log.info("Cannot fetch the certificate of %s: %s" % (location.get_server_key(), err))
            return None
        finally:
            ftp.close()

    def _open(self, credentials):
        location = self.location
        if location.scheme == SCHEME_FTPS:
            ftp = _FtpTls(self._implicit, self._pin, context=self._make_context(), timeout=_TIMEOUT, encoding="utf-8")
        else:
            ftp = _Ftp(timeout=_TIMEOUT, encoding="utf-8")
        try:
            ftp.connect(location.host, location.port)
        except ssl.SSLCertVerificationError as err:
            ftp.close()
            raise self._untrusted(err)
        except _CertificateChanged as err:
            ftp.close()
            raise self._changed(err)
        except (OSError, EOFError, ftplib.Error) as err:
            ftp.close()
            raise ConnectError(_connection_error_message(location, err))
        try:
            if location.scheme == SCHEME_FTPS and not self._implicit:
                ftp.auth()
            if credentials is None:
                user, password = (location.user or "anonymous"), ("" if location.user else "anonymous@")
                if location.user:
                    raise AuthRequired(_("パスワードを入力してください。"))
            else:
                user, password = credentials.user, credentials.password
            ftp.login(user, password)
            if location.scheme == SCHEME_FTPS:
                ftp.prot_p()
        except ssl.SSLCertVerificationError as err:
            ftp.close()
            raise self._untrusted(err)
        except _CertificateChanged as err:
            ftp.close()
            raise self._changed(err)
        except ftplib.error_perm as err:
            ftp.close()
            if str(err).startswith("530"):
                raise AuthRequired(_("ユーザー名またはパスワードが違います。") if credentials else _("このサーバーには、ユーザー名とパスワードが必要です。"))
            if location.scheme == SCHEME_FTPS and str(err)[:3] in ("500", "502", "504", "534"):
                raise ConnectError(_("%(host)s は FTPS（暗号化）に対応していません。\n(%(error)s)") % {
                    "host": location.get_display_host(), "error": err})
            raise RemoteError(_("ログインできませんでした。\n(%(error)s)") % {"error": err})
        except AuthRequired:
            ftp.close()
            raise
        except (OSError, EOFError, ftplib.Error) as err:
            ftp.close()
            raise ConnectError(_connection_error_message(location, err))
        try:
            # ファイル名を UTF-8 でやり取りする。対応していないサーバーでは無視される
            ftp.sendcmd("OPTS UTF8 ON")
        except (ftplib.Error, OSError):
            pass
        return ftp

    def _call(self, func, *args):
        """FTP の操作を呼び、例外を RemoteError にする"""
        try:
            return func(*args)
        except UnicodeDecodeError:
            # UTF-8 に対応していないサーバーでは、日本語のファイル名は Shift_JIS のことが多い
            if self._ftp.encoding == "cp932":
                raise RemoteError(_("ファイル名の文字コードがわかりません。"))
            log.info("switch the encoding to cp932: %s" % self.location.get_server_key())
            self._ftp.encoding = "cp932"
            return self._call(func, *args)
        except ftplib.error_perm as err:
            code = str(err)[:3]
            if code == "550":
                raise RemoteError(_("見つからないか、アクセスが拒否されました。\n(%(error)s)") % {"error": err})
            raise RemoteError(str(err))
        except _CertificateChanged as err:
            # データ用の接続で、許可した証明書と違う証明書が出てきた
            raise ConnectError(str(self._changed(err)))
        except ValueError as err:
            # 改行を含む名前など、FTP のコマンドで送れない名前
            raise RemoteError(_("この名前は、FTP では扱えません。\n(%(error)s)") % {"error": err})
        except (OSError, EOFError, ftplib.Error) as err:
            raise ConnectError(_connection_error_message(self.location, err))

    def check_alive(self):
        self._call(self._ftp.voidcmd, "NOOP")

    def get_initial_path(self):
        return normalize_path(self._call(self._ftp.pwd))

    def list_dir(self, path):
        return self._call(self._list_dir, path)

    def _list_dir(self, path):
        if self._mlsd_supported:
            try:
                return self._list_mlsd(path)
            except ftplib.error_perm as err:
                if str(err)[:3] not in ("500", "501", "502", "504"):
                    raise
                self._mlsd_supported = False
        return self._list_list(path)

    def _list_mlsd(self, path):
        entries = []
        for name, facts in self._ftp.mlsd(path, ["type", "size", "modify", "unix.mode"]):
            kind = facts.get("type", "").lower()
            if kind in ("cdir", "pdir") or name in (".", ".."):
                continue
            is_link = kind.startswith("os.unix=slink")
            is_dir = kind == "dir" or is_link and self._is_dir(join_path(path, name))
            entries.append(Entry(
                name, is_dir, int(facts.get("size", -1)) if not is_dir else -1, _parse_mlsd_time(facts.get("modify")),
                _parse_octal(facts.get("unix.mode")), is_link=is_link))
        return entries

    def _list_list(self, path):
        # LIST に空白を含むパスを渡すと正しく扱えないサーバーがあるので、移動してから取得する
        self._ftp.cwd(path)
        lines = []
        self._ftp.retrlines("LIST", lines.append)
        entries = []
        for line in lines:
            entry = self._parse_list_line(path, line)
            if entry is not None and entry.name not in (".", ".."):
                entries.append(entry)
        return entries

    def _parse_list_line(self, path, line):
        match = _UNIX_LIST.match(line)
        if match:
            name = match.group("name")
            kind = match.group("type")
            if kind == "l":
                name = name.split(" -> ", 1)[0]
                is_dir = self._is_dir(join_path(path, name))
            else:
                is_dir = kind == "d"
            modified = _parse_unix_time(match.group("month"), match.group("day"), match.group("time"))
            precision = 60 if ":" in match.group("time") else 24 * 60 * 60
            return Entry(
                name, is_dir, -1 if is_dir else int(match.group("size")), modified,
                _parse_permission_string(match.group("perms")), precision, is_link=kind == "l")
        match = _DOS_LIST.match(line)
        if match:
            is_dir = match.group("size") == "<DIR>"
            modified = _parse_dos_time(match.group("date"), match.group("time"))
            return Entry(match.group("name"), is_dir, -1 if is_dir else int(match.group("size")), modified, precision=60)
        if line.strip() and not line.lower().startswith("total"):
            log.warning("Cannot parse the LIST line: %s" % line)
        return None

    def _is_dir(self, path):
        """シンボリックリンクの先がフォルダかどうかを、移動できるかで調べる"""
        current = self._ftp.pwd()
        try:
            self._ftp.cwd(path)
            return True
        except ftplib.error_perm:
            return False
        finally:
            self._ftp.cwd(current)

    def get_entry(self, path):
        return self._call(self._get_entry, path)

    def _get_entry(self, path):
        name = posixpath.basename(path)
        if self._is_dir(path):
            return Entry(name, True)
        size = -1
        try:
            self._ftp.voidcmd("TYPE I")
            size = self._ftp.size(path) or -1
        except ftplib.error_perm as err:
            if str(err)[:3] == "550":
                raise
        # 更新日時（UTC）。MDTM に対応していないサーバーでは、わからないままにする
        modified = None
        try:
            response = self._ftp.sendcmd("MDTM " + path)
            if response[:3] == "213":
                modified = _parse_mlsd_time(response[3:].strip())
        except ftplib.error_perm:
            pass
        return Entry(name, False, size, modified)

    def download(self, path, local_path, on_progress=None, offset=0):
        def write(data):
            f.write(data)
            if on_progress is not None:
                on_progress(len(data))

        with open(local_path, "ab" if offset else "wb") as f:
            try:
                self._call(self._ftp.retrbinary, "RETR " + path, write, _BLOCK_SIZE, offset or None)
            except BaseException:
                f.close()
                if not offset:
                    _remove_partial(local_path)
                # 転送を途中でやめると制御用の接続の状態がわからなくなるので、作り直してもらう
                raise

    def upload(self, local_path, path, on_progress=None, offset=0):
        def sent(data):
            if on_progress is not None:
                on_progress(len(data))

        with open(local_path, "rb") as f:
            if offset:
                # 続きからの場合は、末尾に書き足す APPE を使う（REST と STOR の組み合わせより対応しているサーバーが多い）
                f.seek(offset)
                self._call(self._ftp.storbinary, "APPE " + path, f, _BLOCK_SIZE, sent)
            else:
                self._call(self._ftp.storbinary, "STOR " + path, f, _BLOCK_SIZE, sent)

    def create_file(self, path):
        self._call(self._ftp.storbinary, "STOR " + path, io.BytesIO(b""))

    def make_dir(self, path):
        self._call(self._ftp.mkd, path)

    def remove_file(self, path):
        self._call(self._ftp.delete, path)

    def remove_dir(self, path):
        self._call(self._ftp.rmd, path)

    def rename(self, old_path, new_path):
        self._call(self._ftp.rename, old_path, new_path)

    def chmod(self, path, mode):
        try:
            self._call(self._ftp.sendcmd, "SITE CHMOD %03o %s" % (mode & 0o7777, path))
        except ConnectError:
            raise
        except RemoteError as err:
            if str(err)[:3] in ("500", "502", "504"):
                raise RemoteError(_("このサーバーは、パーミッションの変更に対応していません。\n(%(error)s)") % {"error": err})
            raise

    def set_modified(self, path, modified):
        # MFMT は多くの FTP サーバーが対応している拡張コマンド。対応していなければ何もしない
        # wx がロケールを設定していると strftime の結果が変わることがあるため、数字を自分で並べる
        utc = modified.astimezone(datetime.timezone.utc)
        text = "%04d%02d%02d%02d%02d%02d" % (utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second)
        try:
            self._call(self._ftp.sendcmd, "MFMT %s %s" % (text, path))
            return True
        except ConnectError:
            raise
        except RemoteError:
            return False

    def close(self):
        try:
            self._ftp.quit()
        except (OSError, EOFError, ftplib.Error):
            self._ftp.close()


def _parse_octal(text):
    """MLSD の unix.mode（0755 など）を数値にする。わからなければ None"""
    try:
        return int(text, 8) & 0o7777 if text else None
    except ValueError:
        return None


def _parse_mlsd_time(text):
    """MLSD の modify（UTC の YYYYMMDDHHMMSS）を datetime にする"""
    # wx がロケールを設定していると strptime が失敗することがあるため、数字を自分で取り出す
    if not text or len(text) < 14 or not text[:14].isdigit():
        return None
    try:
        return datetime.datetime(
            int(text[0:4]), int(text[4:6]), int(text[6:8]), int(text[8:10]), int(text[10:12]), int(text[12:14]),
            tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def _parse_unix_time(month, day, time_or_year):
    """LIST の日時を datetime にする。サーバーの時刻をそのまま、この PC の時刻として扱う"""
    try:
        month_number = _MONTHS[month.lower()]
        now = datetime.datetime.now()
        if ":" in time_or_year:
            hour, minute = (int(value) for value in time_or_year.split(":"))
            result = datetime.datetime(now.year, month_number, int(day), hour, minute)
            # 年が書かれていないのは半年以内の日時。未来になる場合は去年
            if result > now + datetime.timedelta(days=1):
                result = result.replace(year=now.year - 1)
        else:
            result = datetime.datetime(int(time_or_year), month_number, int(day))
        return result.astimezone()
    except (KeyError, ValueError):
        return None


def _parse_dos_time(date_text, time_text):
    """IIS の LIST の日時（11-26-25 02:15PM）を datetime にする"""
    # AM/PM の解釈はロケールで変わるため、strptime は使わない
    try:
        month, day, year = (int(value) for value in date_text.split("-"))
        hour, minute = (int(value) for value in time_text[:-2].split(":"))
    except ValueError:
        return None
    if year < 100:
        year += 2000 if year < 70 else 1900
    hour %= 12
    if time_text[-2:].upper() == "PM":
        hour += 12
    try:
        return datetime.datetime(year, month, day, hour, minute).astimezone()
    except ValueError:
        return None


def _remove_partial(path):
    """途中まで書いたファイルを消す"""
    try:
        os.remove(path)
    except OSError:
        pass


# ---- SFTP ----

class _RejectUnknownHost:
    """まだ確認していないホスト鍵の場合に、UnknownHostKey を投げる paramiko のポリシー"""

    def missing_host_key(self, client, hostname, key):
        raise UnknownHostKey(_("%(host)s に初めて接続します。") % {"host": hostname}, hostname, key)


class _SftpClient(Client):
    """SFTP の接続"""

    def __init__(self, location, credentials):
        super().__init__(location)
        paramiko = _import_paramiko()
        self._paramiko = paramiko
        self._ssh = paramiko.SSHClient()
        try:
            self._ssh.load_system_host_keys()
        except (OSError, paramiko.SSHException) as err:
            log.warning("Cannot load the system known_hosts: %s" % err)
        if os.path.isfile(get_known_hosts_path()):
            try:
                self._ssh.load_host_keys(get_known_hosts_path())
            except (OSError, paramiko.SSHException) as err:
                log.warning("Cannot load %s: %s" % (get_known_hosts_path(), err))
        with _accepted_host_keys_lock:
            for name, key in _accepted_host_keys:
                self._ssh.get_host_keys().add(name, key.get_name(), key)
        self._ssh.set_missing_host_key_policy(_RejectUnknownHost())
        user = credentials.user if credentials is not None else location.user
        if not user:
            raise AuthRequired(_("ユーザー名を入力してください。"))
        password = credentials.password if credentials is not None else None
        key_file = credentials.key_file if credentials is not None else ""
        if key_file and not os.path.isfile(key_file):
            raise AuthRequired(_("鍵ファイル %(path)s が見つかりません。") % {"path": key_file})
        try:
            sock = open_socket(location.host, location.port, _TIMEOUT) if get_proxy() is not None else None
            self._ssh.connect(
                location.host, location.port, username=user, password=password,
                key_filename=key_file or None, passphrase=password if key_file else None, sock=sock,
                timeout=_TIMEOUT, banner_timeout=_TIMEOUT, auth_timeout=_TIMEOUT,
                # パスワードがわかっている場合も、鍵による認証を先に試す
                allow_agent=True, look_for_keys=True)
            self._sftp = self._ssh.open_sftp()
            # 応答が返ってこないときに、いつまでも待たないようにする（中止もできなくなるため）
            self._sftp.get_channel().settimeout(_TIMEOUT)
        except UnknownHostKey:
            self._ssh.close()
            raise
        except paramiko.BadHostKeyException:
            self._ssh.close()
            raise ConnectError(_(
                "%(host)s のホスト鍵が、以前に接続したときと違います。\n"
                "なりすましの可能性があるため、接続を中止しました。サーバーの管理者に確認してください。") % {"host": location.get_display_host()})
        except paramiko.PasswordRequiredException:
            self._ssh.close()
            raise AuthRequired(_("鍵ファイルのパスフレーズを入力してください。"))
        except paramiko.AuthenticationException:
            self._ssh.close()
            if key_file:
                message = _("鍵ファイル、パスフレーズ、またはユーザー名が違います。")
            elif password:
                message = _("ユーザー名またはパスワードが違います。")
            else:
                message = _("パスワードを入力してください。")
            raise AuthRequired(message)
        except (OSError, EOFError, paramiko.SSHException) as err:
            self._ssh.close()
            raise ConnectError(_connection_error_message(location, err))

    def _call(self, func, *args):
        try:
            return func(*args)
        except FileNotFoundError:
            raise RemoteError(_("見つかりません。"))
        except PermissionError:
            raise RemoteError(_("アクセスが拒否されました。"))
        except (socket.timeout, socket.gaierror, ConnectionError, EOFError, self._paramiko.SSHException) as err:
            raise ConnectError(_connection_error_message(self.location, err))
        except UnicodeDecodeError:
            raise RemoteError(_("ファイル名の文字コードがわかりません。"))
        except OSError as err:
            # SFTP サーバーが返したエラー
            raise RemoteError(_describe(err))

    def check_alive(self):
        if not self._ssh.get_transport() or not self._ssh.get_transport().is_active():
            raise ConnectError(_connection_error_message(self.location, ConnectionError(_("接続が切れました"))))
        self._call(self._sftp.normalize, ".")

    def get_real_path(self, path):
        try:
            return normalize_path(self._call(self._sftp.normalize, path))
        except ConnectError:
            raise
        except RemoteError:
            return None

    def get_initial_path(self):
        return normalize_path(self._call(self._sftp.normalize, "."))

    def list_dir(self, path):
        return self._call(self._list_dir, path)

    def _list_dir(self, path):
        entries = []
        for attributes in self._sftp.listdir_attr(path):
            mode = attributes.st_mode or 0
            is_link = stat.S_ISLNK(mode)
            if is_link:
                try:
                    mode = self._sftp.stat(join_path(path, attributes.filename)).st_mode or 0
                except OSError:
                    pass  # リンク先がない
            entries.append(self._make_entry(attributes.filename, mode, attributes, is_link))
        return entries

    def _make_entry(self, name, mode, attributes, is_link=False):
        is_dir = stat.S_ISDIR(mode)
        modified = None
        if attributes.st_mtime is not None:
            modified = datetime.datetime.fromtimestamp(attributes.st_mtime, datetime.timezone.utc)
        size = attributes.st_size if attributes.st_size is not None and not is_dir else -1
        permissions = (attributes.st_mode & 0o7777) if attributes.st_mode is not None else None
        return Entry(name, is_dir, size, modified, permissions, is_link=is_link)

    def get_entry(self, path):
        attributes = self._call(self._sftp.stat, path)
        return self._make_entry(posixpath.basename(path), attributes.st_mode or 0, attributes)

    def download(self, path, local_path, on_progress=None, offset=0):
        start = offset

        def read_all():
            with self._sftp.open(path, "rb") as remote, open(local_path, "ab" if start else "wb") as f:
                size = remote.stat().st_size or 0
                offset = start
                remote.seek(offset)
                # 読み込みの要求をまとめて送ると速いが、paramiko の prefetch は要求を送るスレッドが残り、
                # 中止して接続を閉じるとそのスレッドで例外になる。そのため、一定の大きさごとに readv で読む
                while offset < size:
                    end = min(size, offset + _SFTP_WINDOW)
                    chunks = [(start, min(_SFTP_CHUNK, end - start)) for start in range(offset, end, _SFTP_CHUNK)]
                    for data in remote.readv(chunks):
                        f.write(data)
                        if on_progress is not None:
                            on_progress(len(data))
                    offset = end
                # 大きさを調べた後に増えた分
                while True:
                    data = remote.read(_BLOCK_SIZE)
                    if not data:
                        break
                    f.write(data)
                    if on_progress is not None:
                        on_progress(len(data))

        try:
            self._call(read_all)
        except BaseException:
            if not start:
                _remove_partial(local_path)
            raise

    def upload(self, local_path, path, on_progress=None, offset=0):
        def write_all():
            with open(local_path, "rb") as f, self._sftp.open(path, "ab" if offset else "wb") as remote:
                # 応答を待たずに続けて送る。閉じるときにまとめて結果を確かめる
                remote.set_pipelined(True)
                f.seek(offset)
                while True:
                    data = f.read(_SFTP_CHUNK)
                    if not data:
                        break
                    remote.write(data)
                    if on_progress is not None:
                        on_progress(len(data))

        self._call(write_all)

    def create_file(self, path):
        def create():
            self._sftp.open(path, "wb").close()
        self._call(create)

    def make_dir(self, path):
        self._call(self._sftp.mkdir, path)

    def remove_file(self, path):
        self._call(self._sftp.remove, path)

    def remove_dir(self, path):
        self._call(self._sftp.rmdir, path)

    def rename(self, old_path, new_path):
        self._call(self._sftp.rename, old_path, new_path)

    def chmod(self, path, mode):
        self._call(self._sftp.chmod, path, mode & 0o7777)

    def set_modified(self, path, modified):
        timestamp = modified.timestamp()
        self._call(self._sftp.utime, path, (timestamp, timestamp))
        return True

    def close(self):
        self._ssh.close()


# ---- 接続の使い回し ----

class SessionPool:
    """一覧の取得に使う接続を、サーバーごとに使い回す"""

    def __init__(self):
        self._lock = threading.Lock()
        # サーバーの key -> (Client, 使用中を表す Lock)
        self._sessions = {}

    def run(self, location, func, *args):
        """
        (別スレッド)接続を用意して func(client, *args) を呼び、その戻り値を返す。
        使い回す接続は、func を呼ぶ前に切れていないかを確かめ、切れていればつなぎ直す。
        func の途中で切れた場合はやり直さない（フォルダの作成などを2回実行しないため）。
        func が RemoteError 以外の例外（中止など）で終わった場合は、接続の状態がわからないので捨てる。
        """
        key = location.get_server_key()
        with self._lock:
            client, busy = self._sessions.get(key, (None, None))
        # 中止されて置き去りにしたスレッドが使っている場合は、別の接続を作る
        if busy is not None and busy.acquire(timeout=1):
            try:
                alive = True
                try:
                    client.check_alive()
                except RemoteError:
                    alive = False
                    log.info("reconnect to %s" % key)
                    self.discard(location, client)
                if alive:
                    return self._call(location, client, func, args)
            finally:
                busy.release()
        client = connect(location, credential_store.get(location))
        busy = threading.Lock()
        with busy:
            with self._lock:
                old = self._sessions.get(key)
                self._sessions[key] = (client, busy)
            if old is not None:
                _close_quietly(old[0])
            return self._call(location, client, func, args)

    def _call(self, location, client, func, args):
        try:
            return func(client, *args)
        except ConnectError:
            self.discard(location, client)
            raise
        except RemoteError:
            raise
        except BaseException:
            self.discard(location, client)
            raise

    def discard(self, location, client=None):
        """接続を捨てる。client を指定した場合は、その接続を使っているときだけ捨てる"""
        key = location.get_server_key()
        with self._lock:
            current = self._sessions.get(key)
            if current is None or (client is not None and current[0] is not client):
                return
            del self._sessions[key]
        _close_quietly(current[0])

    def close_all(self):
        with self._lock:
            sessions, self._sessions = self._sessions, {}
        for client, dummy in sessions.values():
            _close_quietly(client)


def _close_quietly(client):
    try:
        client.close()
    except Exception as err:
        log.debug("close failed: %s" % err)


pool = SessionPool()
