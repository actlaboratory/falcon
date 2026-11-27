# -*- coding: utf-8 -*-
# Falcon FTP / FTPS connection tests
# Note: All comments except these top lines will be written in Japanese.

"""
FTP・FTPS（Explicit）の接続テストです。ローカルで pyftpdlib のサーバーを起動して試します。
実行: python -m unittest discover -s tests -p "test_*.py"
"""

import ftplib
import os
import unittest

import remote_servers
import remote_test_base
from remote_test_base import RemoteTestCase, ClientOperationsMixin, TransferJobMixin

import remote_storage


class FtpTestCase(RemoteTestCase):
    """暗号化しない FTP のサーバーを起動する"""

    def setUp(self):
        super().setUp()
        self.server = remote_servers.FtpServer(self.server_root)
        self.addCleanup(self.server.close)
        self.location = remote_storage.parse_url("ftp://%s@127.0.0.1:%d/" % (remote_servers.USER, self.server.port))
        self.credentials = remote_storage.Credentials(remote_servers.USER, remote_servers.PASSWORD)


class TestFtpOperations(ClientOperationsMixin, FtpTestCase):
    """FTP の操作"""

    def test_list_with_list_command(self):
        # MLSD に対応していないサーバーでは LIST の結果を読む
        client = self.connect()
        client._mlsd_supported = False
        entries = {entry.name: entry for entry in client.list_dir("/")}
        self.assertEqual(set(entries), {"big.bin", remote_test_base.JAPANESE_NAME, "folder"})
        self.assertEqual(entries["big.bin"].size, len(remote_test_base.BIG_CONTENT))
        self.assertTrue(entries["folder"].is_dir)
        self.assertIsNotNone(entries["big.bin"].modified)

    def test_list_command_includes_hidden_files(self):
        # LIST では . で始まるファイルも一覧に入れる（LIST -a）
        with open(os.path.join(self.server_root, ".hidden"), "wb") as f:
            f.write(b"x")
        client = self.connect()
        client._mlsd_supported = False
        self.assertIn(".hidden", [entry.name for entry in client.list_dir("/")])
        self.assertIs(client._list_all_supported, True)

    def test_list_command_without_list_all(self):
        # LIST -a を受け付けないサーバーでは LIST を使う
        client = self.connect()
        client._mlsd_supported = False
        original = client._ftp.retrlines

        def retrlines(command, callback=None):
            if command == "LIST -a":
                raise ftplib.error_perm("501 Invalid option")
            return original(command, callback)

        client._ftp.retrlines = retrlines
        self.assertIn("big.bin", [entry.name for entry in client.list_dir("/")])
        self.assertIs(client._list_all_supported, False)

    def test_chmod(self):
        # pyftpdlib は SITE CHMOD に対応している（Windows では読み取り専用かどうかだけが変わる）
        client = self.connect()
        client.chmod("/big.bin", 0o444)
        self.assertFalse(os.access(os.path.join(self.server_root, "big.bin"), os.W_OK))
        client.chmod("/big.bin", 0o644)
        self.assertTrue(os.access(os.path.join(self.server_root, "big.bin"), os.W_OK))

    def test_password_command_is_masked(self):
        self.connect()
        log = self.get_log()
        self.assertIn("> PASS ****", log)
        self.assert_password_not_logged()


class TestFtpTransferJobs(TransferJobMixin, FtpTestCase):
    """FTP でのダウンロード・アップロード・削除"""


class TestFtpConnectErrors(FtpTestCase):
    """FTP の接続の失敗"""

    def test_wrong_password(self):
        with self.assertRaises(remote_storage.AuthRequired):
            remote_storage.connect(self.location, remote_storage.Credentials(remote_servers.USER, "wrong"))
        self.assertNotIn("PASS wrong", self.get_log())

    def test_password_required(self):
        # ユーザー名だけの URL で、パスワードがわからない場合
        with self.assertRaises(remote_storage.AuthRequired):
            remote_storage.connect(self.location, None)

    def test_connection_refused(self):
        self.server.close()
        with self.assertRaises(remote_storage.ConnectError):
            remote_storage.connect(self.location, self.credentials)
        self.assertIn("cannot connect to %s" % self.location.get_server_key(), self.get_log())

    def test_proxy_refused(self):
        # CONNECT を拒否するプロキシ
        proxy = remote_servers.RefusingProxy()
        self.addCleanup(proxy.close)
        remote_storage.set_proxy(("127.0.0.1", proxy.port))
        self.addCleanup(remote_storage.set_proxy, None)
        with self.assertRaises(remote_storage.ConnectError):
            remote_storage.connect(self.location, self.credentials)
        self.assertIn("the proxy refused CONNECT", self.get_log())


@unittest.skipUnless(remote_servers.has_ftps_support(), "pyOpenSSL is required for the FTPS server")
class FtpsTestCase(RemoteTestCase):
    """自己署名証明書を使う Explicit FTPS のサーバーを起動する"""

    def setUp(self):
        super().setUp()
        certfile = os.path.join(self.work, "server.pem")
        self.certificate = remote_servers.make_certificate(certfile)
        self.server = remote_servers.FtpServer(self.server_root, tls=True, certfile=certfile)
        self.addCleanup(self.server.close)
        self.location = remote_storage.parse_url("ftps://%s@127.0.0.1:%d/" % (remote_servers.USER, self.server.port))
        self.credentials = remote_storage.Credentials(remote_servers.USER, remote_servers.PASSWORD)

    def trust_certificate(self):
        remote_storage.certificate_trust.trust(
            self.location, remote_storage.get_certificate_fingerprint(self.certificate))


class TestFtpsCertificate(FtpsTestCase):
    """FTPS の証明書の確認"""

    def test_untrusted_certificate(self):
        with self.assertRaises(remote_storage.UntrustedCertificate) as context:
            remote_storage.connect(self.location, self.credentials)
        err = context.exception
        self.assertFalse(err.changed)
        # 利用者に見せる指紋が、サーバーの証明書の指紋と一致すること
        self.assertEqual(err.fingerprint, remote_storage.get_certificate_fingerprint(self.certificate))
        self.assertIn("localhost", err.details)

    def test_trusted_certificate(self):
        self.trust_certificate()
        client = self.connect()
        self.assertIn("big.bin", [entry.name for entry in client.list_dir("/")])
        log = self.get_log()
        self.assertIn("control connection TLS", log)
        # データ用の接続で TLS のセッションを再利用していること
        self.assertIn("data connection TLS session reused: True", log)

    def test_trusted_certificate_is_saved(self):
        self.trust_certificate()
        # 保存したファイルから読み直しても使えること
        remote_storage.certificate_trust = remote_storage.TrustStore(os.path.join(self.work, "trusted_certificates.json"))
        self.connect().check_alive()

    def test_changed_certificate(self):
        remote_storage.certificate_trust.trust(self.location, "SHA256:" + ":".join(["00"] * 32))
        with self.assertRaises(remote_storage.UntrustedCertificate) as context:
            remote_storage.connect(self.location, self.credentials)
        self.assertTrue(context.exception.changed)
        self.assertEqual(context.exception.fingerprint, remote_storage.get_certificate_fingerprint(self.certificate))


class TestFtpsNotSupported(FtpTestCase):
    """FTPS に対応していないサーバー"""

    def test_auth_tls_rejected_with_530(self):
        # AUTH TLS に 530 を返すサーバー（TLS を使わない vsftpd など）は、パスワードの誤りとして扱わない
        location = remote_storage.parse_url("ftps://%s@127.0.0.1:%d/" % (remote_servers.USER, self.server.port))

        def auth(ftp):
            raise ftplib.error_perm("530 Please login with USER and PASS.")

        self._patch(remote_storage._FtpTls, "auth", auth)
        with self.assertRaises(remote_storage.ConnectError) as context:
            remote_storage.connect(location, self.credentials)
        self.assertNotIsInstance(context.exception, remote_storage.AuthRequired)


class TestFtpsOperations(ClientOperationsMixin, FtpsTestCase):
    """証明書を許可した FTPS の操作（データ用の接続も暗号化する）"""

    def setUp(self):
        super().setUp()
        self.trust_certificate()


class TestFtpsTransferJobs(TransferJobMixin, FtpsTestCase):
    """FTPS でのダウンロード・アップロード・削除"""

    def setUp(self):
        super().setUp()
        self.trust_certificate()


if __name__ == "__main__":
    unittest.main()
