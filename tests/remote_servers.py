# -*- coding: utf-8 -*-
# Falcon test servers for FTP / FTPS / SFTP
# Note: All comments except these top lines will be written in Japanese.

"""
接続テスト用の、ローカルで動く FTP・FTPS・SFTP のサーバーです。
どれも 127.0.0.1 の空いているポートで待ち受け、一時フォルダを公開します。
FTP・FTPS は pyftpdlib（requirements-test.txt）、SFTP は paramiko のサーバー機能を使います。
"""

import datetime
import os
import posixpath
import socket
import threading
import warnings

USER = "tester"
PASSWORD = "test-password"


def setup_falcon_path():
    """falcon のモジュールを読み込めるようにし、翻訳の関数 _ がなければ用意する"""
    import builtins
    import sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    if not hasattr(builtins, "_"):
        builtins._ = lambda text: text


def has_ftps_support():
    """FTPS のテスト用サーバーを動かせるか（pyOpenSSL があるか）"""
    try:
        import OpenSSL  # noqa: F401
        return True
    except ImportError:
        return False


def make_certificate(path, common_name="localhost"):
    """自己署名証明書と秘密鍵を PEM で path に書き、証明書（DER）を返す"""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=5)).not_valid_after(now + datetime.timedelta(days=1))
            .sign(key, hashes.SHA256()))
    with open(path, "wb") as f:
        f.write(key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    return cert.public_bytes(serialization.Encoding.DER)


class FtpServer:
    """pyftpdlib の FTP（tls=True なら Explicit FTPS）サーバー"""

    def __init__(self, root, tls=False, certfile=None):
        import logging
        from pyftpdlib.authorizers import DummyAuthorizer
        from pyftpdlib.servers import FTPServer
        if tls:
            from pyftpdlib.handlers import TLS_FTPHandler as base
        else:
            from pyftpdlib.handlers import FTPHandler as base
        # pyftpdlib のログ（標準エラー出力）は、テストの結果を読みにくくするので出さない
        logging.getLogger("pyftpdlib").setLevel(logging.CRITICAL)
        authorizer = DummyAuthorizer()
        authorizer.add_user(USER, PASSWORD, root, perm="elradfmwMT")
        # ハンドラーの設定はクラス変数なので、サーバーごとに派生クラスを作る
        attributes = {"authorizer": authorizer, "timeout": 30}
        if tls:
            attributes.update(certfile=certfile, tls_control_required=True, tls_data_required=True)
        handler = type("Handler", (base,), attributes)
        self._server = FTPServer(("127.0.0.1", 0), handler)
        self.port = self._server.socket.getsockname()[1]
        self._thread = threading.Thread(target=self._server.serve_forever, kwargs={"timeout": 0.1}, daemon=True)
        self._thread.start()

    def drop_connections(self):
        """
        接続しているクライアントとの接続を、サーバーの側から切る（待ち受けは続ける）。
        pyftpdlib の処理はスレッドに安全ではないので、サーバーのスレッドで切る。
        """
        from pyftpdlib.handlers import FTPHandler
        done = threading.Event()

        def drop():
            for handler in list(self._server.ioloop.socket_map.values()):
                if isinstance(handler, FTPHandler):
                    handler.close()
            done.set()

        self._server.ioloop.call_later(0, drop)
        done.wait(5)

    def close(self):
        """サーバーを止める。2回呼んでもよい"""
        if not self._thread.is_alive():
            return
        # ほかのスレッドから閉じると、待ち受け中のスレッドで例外になるので、サーバーのスレッドで閉じる
        self._server.ioloop.call_later(0, self._server.close_all)
        self._thread.join(5)


class RefusingProxy:
    """CONNECT を 403 で拒否する HTTP プロキシ"""

    def __init__(self):
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(5)
        self.port = self._listener.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        while True:
            try:
                conn, dummy = self._listener.accept()
            except OSError:
                break
            with conn:
                try:
                    conn.recv(4096)
                    conn.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
                except OSError:
                    pass

    def close(self):
        self._listener.close()
        self._thread.join(5)


# ---- SFTP ----

def _import_paramiko():
    warnings.filterwarnings("ignore", message=".*32-bit Python.*")
    import paramiko
    return paramiko


class SftpServer:
    """
    paramiko の SFTP サーバー。root を / として公開する。
    パスワード（USER / PASSWORD）と、authorized_key に指定した公開鍵での認証を受け付ける。
    """

    def __init__(self, root, host_key=None, authorized_key=None):
        paramiko = _import_paramiko()
        self.root = root
        self.host_key = host_key or paramiko.ECDSAKey.generate()
        self.authorized_key = authorized_key
        # クライアントが送ってきたパスワード（パスフレーズを送っていないかを確かめるため）
        self.received_passwords = []
        self._transports = []
        self._closing = False
        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(5)
        self._listener.settimeout(0.2)
        self.port = self._listener.getsockname()[1]
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def _accept_loop(self):
        paramiko = _import_paramiko()
        sftp_server_class = _make_sftp_server_class(paramiko, self.root)
        while not self._closing:
            try:
                sock, dummy = self._listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            transport = paramiko.Transport(sock)
            transport.add_server_key(self.host_key)
            transport.set_subsystem_handler("sftp", paramiko.SFTPServer, sftp_server_class)
            self._transports.append(transport)
            try:
                transport.start_server(server=_make_server_interface(paramiko, self.authorized_key, self.received_passwords))
            except (paramiko.SSHException, EOFError, OSError):
                # 鍵の確認で接続を中止したクライアントなど
                continue

    def drop_connections(self):
        """接続しているクライアントとの接続を、サーバーの側から切る（待ち受けは続ける）"""
        for transport in self._transports:
            transport.close()

    def close(self):
        self._closing = True
        self._listener.close()
        self._thread.join(5)
        self.drop_connections()


def _make_server_interface(paramiko, authorized_key, received_passwords):
    """認証を受け付ける paramiko.ServerInterface を作る"""

    class _Server(paramiko.ServerInterface):
        def get_allowed_auths(self, username):
            return "password,publickey"

        def check_auth_password(self, username, password):
            received_passwords.append(password)
            if username == USER and password == PASSWORD:
                return paramiko.AUTH_SUCCESSFUL
            return paramiko.AUTH_FAILED

        def check_auth_publickey(self, username, key):
            if username == USER and authorized_key is not None and key == authorized_key:
                return paramiko.AUTH_SUCCESSFUL
            return paramiko.AUTH_FAILED

        def check_channel_request(self, kind, chanid):
            if kind == "session":
                return paramiko.OPEN_SUCCEEDED
            return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    return _Server()


def _make_sftp_server_class(paramiko, root):
    """root を / として公開する paramiko.SFTPServerInterface のクラスを作る"""

    def to_local(path):
        # SFTP のパスは / 区切り。root の外には出さない
        return os.path.join(root, *[part for part in posixpath.normpath("/" + path).split("/") if part])

    def convert_error(err):
        return paramiko.SFTPServer.convert_errno(err.errno)

    def set_file_attr(local, attr):
        # paramiko の set_file_attr は Windows ではパーミッションを変えないので、ここで変える
        # （Windows では読み取り専用かどうかだけが変わる）
        if attr._flags & attr.FLAG_PERMISSIONS:
            os.chmod(local, attr.st_mode)
        paramiko.SFTPServer.set_file_attr(local, attr)

    class _Handle(paramiko.SFTPHandle):
        def stat(self):
            try:
                return paramiko.SFTPAttributes.from_stat(os.fstat(self.readfile.fileno()))
            except OSError as err:
                return convert_error(err)

        def chattr(self, attr):
            try:
                set_file_attr(self.filename, attr)
                return paramiko.SFTP_OK
            except OSError as err:
                return convert_error(err)

    class _SftpServer(paramiko.SFTPServerInterface):
        def canonicalize(self, path):
            return posixpath.normpath("/" + path)

        def list_folder(self, path):
            local = to_local(path)
            try:
                result = []
                for name in os.listdir(local):
                    attributes = paramiko.SFTPAttributes.from_stat(os.stat(os.path.join(local, name)))
                    attributes.filename = name
                    result.append(attributes)
                return result
            except OSError as err:
                return convert_error(err)

        def stat(self, path):
            try:
                return paramiko.SFTPAttributes.from_stat(os.stat(to_local(path)))
            except OSError as err:
                return convert_error(err)

        def lstat(self, path):
            try:
                return paramiko.SFTPAttributes.from_stat(os.lstat(to_local(path)))
            except OSError as err:
                return convert_error(err)

        def open(self, path, flags, attr):
            local = to_local(path)
            try:
                # Windows では、改行の変換をしないように O_BINARY が必要
                fd = os.open(local, flags | getattr(os, "O_BINARY", 0), 0o666)
            except OSError as err:
                return convert_error(err)
            if flags & os.O_WRONLY:
                mode = "ab" if flags & os.O_APPEND else "wb"
            elif flags & os.O_RDWR:
                mode = "a+b" if flags & os.O_APPEND else "r+b"
            else:
                mode = "rb"
            try:
                f = os.fdopen(fd, mode)
            except OSError as err:
                os.close(fd)
                return convert_error(err)
            handle = _Handle(flags)
            handle.filename = local
            handle.readfile = f
            handle.writefile = f
            return handle

        def remove(self, path):
            try:
                os.remove(to_local(path))
            except OSError as err:
                return convert_error(err)
            return paramiko.SFTP_OK

        def rename(self, oldpath, newpath):
            try:
                os.rename(to_local(oldpath), to_local(newpath))
            except OSError as err:
                return convert_error(err)
            return paramiko.SFTP_OK

        def posix_rename(self, oldpath, newpath):
            return self.rename(oldpath, newpath)

        def mkdir(self, path, attr):
            try:
                os.mkdir(to_local(path))
            except OSError as err:
                return convert_error(err)
            return paramiko.SFTP_OK

        def rmdir(self, path):
            try:
                os.rmdir(to_local(path))
            except OSError as err:
                return convert_error(err)
            return paramiko.SFTP_OK

        def chattr(self, path, attr):
            try:
                set_file_attr(to_local(path), attr)
            except OSError as err:
                return convert_error(err)
            return paramiko.SFTP_OK

    return _SftpServer
