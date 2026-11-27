# -*- coding: utf-8 -*-
# Falcon SFTP connection tests
# Note: All comments except these top lines will be written in Japanese.

"""
SFTP の接続テストです。ローカルで paramiko の SFTP サーバーを起動して試します。
実行: python -m unittest discover -s tests -p "test_*.py"
"""

import os
import unittest

import remote_servers
from remote_test_base import RemoteTestCase, ClientOperationsMixin, TransferJobMixin

import remote_storage

paramiko = remote_servers._import_paramiko()


class SftpTestCase(RemoteTestCase):
    """SFTP のサーバーを起動する。ホスト鍵は確認済みにしておく"""

    # True の場合は、ホスト鍵を確認済みにしない
    unknown_host = False

    def setUp(self):
        super().setUp()
        self.client_key = paramiko.ECDSAKey.generate()
        self.server = remote_servers.SftpServer(self.server_root, authorized_key=self.client_key)
        self.addCleanup(self.server.close)
        self.location = remote_storage.parse_url("sftp://%s@127.0.0.1:%d/" % (remote_servers.USER, self.server.port))
        self.credentials = remote_storage.Credentials(remote_servers.USER, remote_servers.PASSWORD)
        # PC の ssh エージェントや ~/.ssh の鍵を使わない（テストの結果が PC によって変わらないように）
        self._patch(paramiko.SSHClient, "connect", _without_agent_and_keys(paramiko.SSHClient.connect))
        if not self.unknown_host:
            remote_storage.add_known_host(self.make_unknown_host_key_error(self.server.host_key))

    def host_key_name(self):
        return "[127.0.0.1]:%d" % self.server.port

    def make_unknown_host_key_error(self, key):
        return remote_storage.UnknownHostKey("", self.host_key_name(), key)


def _without_agent_and_keys(connect):
    def wrapper(self, *args, **kwargs):
        kwargs["allow_agent"] = False
        kwargs["look_for_keys"] = False
        return connect(self, *args, **kwargs)
    return wrapper


class TestSftpOperations(ClientOperationsMixin, SftpTestCase):
    """SFTP の操作"""

    def test_chmod(self):
        # Windows の上で動くテストのサーバーでは、読み取り専用かどうかだけが変わる
        client = self.connect()
        client.chmod("/big.bin", 0o444)
        self.assertFalse(os.access(os.path.join(self.server_root, "big.bin"), os.W_OK))
        client.chmod("/big.bin", 0o644)
        self.assertTrue(os.access(os.path.join(self.server_root, "big.bin"), os.W_OK))

    def test_get_real_path(self):
        client = self.connect()
        self.assertEqual(client.get_real_path("/folder/../folder/inner"), "/folder/inner")

    def test_transport_is_logged(self):
        self.connect()
        log = self.get_log()
        self.assertIn("host key ecdsa-sha2-nistp256", log)
        # paramiko のログも falcon のログに入ること
        self.assertIn("paramiko.transport", log)


class TestSftpTransferJobs(TransferJobMixin, SftpTestCase):
    """SFTP でのダウンロード・アップロード・削除"""


class TestSftpHostKey(SftpTestCase):
    """SFTP のホスト鍵の確認"""

    unknown_host = True

    def test_unknown_host_key(self):
        with self.assertRaises(remote_storage.UnknownHostKey) as context:
            remote_storage.connect(self.location, self.credentials)
        err = context.exception
        self.assertEqual(err.key, self.server.host_key)
        self.assertTrue(err.get_fingerprint().startswith("ecdsa-sha2-nistp256 SHA256:"))

    def test_accept_host_key(self):
        with self.assertRaises(remote_storage.UnknownHostKey) as context:
            remote_storage.connect(self.location, self.credentials)
        remote_storage.add_known_host(context.exception)
        self.connect().check_alive()
        # known_hosts に保存され、falcon を起動し直しても（覚えている鍵を消しても）使えること
        self.assertTrue(os.path.isfile(remote_storage.get_known_hosts_path()))
        del remote_storage._accepted_host_keys[:]
        self.connect().check_alive()

    def test_changed_host_key(self):
        remote_storage.add_known_host(self.make_unknown_host_key_error(paramiko.ECDSAKey.generate()))
        with self.assertRaises(remote_storage.ConnectError):
            remote_storage.connect(self.location, self.credentials)
        self.assertIn("the host key has changed", self.get_log())


class TestSftpAuthentication(SftpTestCase):
    """SFTP の認証"""

    def test_wrong_password(self):
        with self.assertRaises(remote_storage.AuthRequired):
            remote_storage.connect(self.location, remote_storage.Credentials(remote_servers.USER, "wrong"))

    def test_password_required(self):
        # パスワードも使える鍵もない場合は、接続の失敗ではなく、パスワードの入力を求める
        with self.assertRaises(remote_storage.AuthRequired):
            remote_storage.connect(self.location, None)

    def test_user_required(self):
        location = remote_storage.parse_url("sftp://127.0.0.1:%d/" % self.server.port)
        with self.assertRaises(remote_storage.AuthRequired):
            remote_storage.connect(location, None)

    def test_key_file(self):
        key_file = os.path.join(self.work, "id_ecdsa")
        self.client_key.write_private_key_file(key_file)
        client = self.connect_with(remote_storage.Credentials(remote_servers.USER, None, key_file))
        client.check_alive()

    def test_key_file_with_passphrase(self):
        key_file = os.path.join(self.work, "id_ecdsa")
        passphrase = "key-secret-42"
        self.client_key.write_private_key_file(key_file, password=passphrase)
        with self.assertRaises(remote_storage.AuthRequired):
            remote_storage.connect(self.location, remote_storage.Credentials(remote_servers.USER, None, key_file))
        client = self.connect_with(remote_storage.Credentials(remote_servers.USER, passphrase, key_file))
        client.check_alive()
        self.assertNotIn(passphrase, self.get_log())

    def test_wrong_passphrase(self):
        key_file = os.path.join(self.work, "id_ecdsa")
        self.client_key.write_private_key_file(key_file, password="key-secret-42")
        with self.assertRaises(remote_storage.AuthRequired):
            remote_storage.connect(self.location, remote_storage.Credentials(remote_servers.USER, "wrong", key_file))

    def test_passphrase_is_not_sent_as_password(self):
        # サーバーが受け付けない鍵の場合も、パスフレーズをログインのパスワードとして送らない
        key_file = os.path.join(self.work, "id_other")
        paramiko.ECDSAKey.generate().write_private_key_file(key_file, password="key-secret-42")
        with self.assertRaises(remote_storage.AuthRequired):
            remote_storage.connect(self.location, remote_storage.Credentials(remote_servers.USER, "key-secret-42", key_file))
        self.assertNotIn("key-secret-42", self.server.received_passwords)

    def test_missing_key_file(self):
        key_file = os.path.join(self.work, "missing_key")
        with self.assertRaises(remote_storage.AuthRequired):
            remote_storage.connect(self.location, remote_storage.Credentials(remote_servers.USER, None, key_file))

    def connect_with(self, credentials):
        client = remote_storage.connect(self.location, credentials)
        self.addCleanup(client.close)
        return client


if __name__ == "__main__":
    unittest.main()
