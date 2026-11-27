# -*- coding: utf-8 -*-
# Falcon remote storage test base
# Note: All comments except these top lines will be written in Japanese.

"""
FTP・FTPS・SFTP の接続テストに共通の処理です。
- RemoteTestCase: 一時フォルダ・ログの記録・remote_storage の状態（資格情報・証明書・ホスト鍵）を、テストごとに分ける
- ClientOperationsMixin: どの方式でも同じように動くべき、Client の操作のテスト
- TransferJobMixin: remote_transfer のダウンロード・アップロード・削除のジョブのテスト
派生クラスでは、サーバーを起動して self.location と self.credentials を決め、make_client() を作る。
"""

import datetime
import io
import logging
import os
import shutil
import tempfile
import unittest
from unittest import mock

import remote_servers

remote_servers.setup_falcon_path()

import remote_storage  # noqa: E402
import remote_transfer  # noqa: E402

# 一覧に置くファイルの中身。転送の途中の区切り（64KB・32KB）をまたぐ大きさにする
BIG_CONTENT = bytes(range(256)) * 1000
JAPANESE_NAME = "日本語のファイル.txt"


def make_tree(root):
    """テスト用のファイルとフォルダを root に作る"""
    with open(os.path.join(root, "big.bin"), "wb") as f:
        f.write(BIG_CONTENT)
    with open(os.path.join(root, JAPANESE_NAME), "wb") as f:
        f.write("こんにちは".encode("utf-8"))
    os.makedirs(os.path.join(root, "folder", "inner"))
    with open(os.path.join(root, "folder", "one.txt"), "wb") as f:
        f.write(b"one")
    with open(os.path.join(root, "folder", "inner", "two.txt"), "wb") as f:
        f.write(b"two")


def read(path):
    with open(path, "rb") as f:
        return f.read()


class RemoteTestCase(unittest.TestCase):
    """接続テストの基本。テストごとに一時フォルダを作り、remote_storage の状態を分ける"""

    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="falcon_test_")
        self.addCleanup(shutil.rmtree, self.work, ignore_errors=True)
        # サーバーが公開するフォルダと、ダウンロード先などに使うローカルのフォルダ
        self.server_root = os.path.join(self.work, "server")
        self.local = os.path.join(self.work, "local")
        os.makedirs(self.server_root)
        os.makedirs(self.local)
        make_tree(self.server_root)

        # 資格情報・証明書・ホスト鍵を、PC の設定や資格情報マネージャーと混ぜない
        store = remote_storage.CredentialStore()
        store._read_windows = lambda key: None
        self._patch(remote_storage, "credential_store", store)
        self._patch(remote_storage, "certificate_trust",
                    remote_storage.TrustStore(os.path.join(self.work, "trusted_certificates.json")))
        known_hosts = os.path.join(self.work, "known_hosts")
        self._patch(remote_storage, "get_known_hosts_path", lambda: known_hosts)
        self._patch(remote_storage, "_accepted_host_keys", [])
        self._patch(remote_storage, "pool", remote_storage.SessionPool())
        self.addCleanup(lambda: remote_storage.pool.close_all())
        remote_storage.set_proxy(None)

        # ログを記録する
        self.log_stream = io.StringIO()
        handler = logging.StreamHandler(self.log_stream)
        handler.setFormatter(logging.Formatter("%(name)s - %(levelname)s - %(message)s"))
        logger = logging.getLogger("falcon")
        old_level = logger.level
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        self.addCleanup(logger.removeHandler, handler)
        self.addCleanup(logger.setLevel, old_level)

    def _patch(self, target, name, value):
        patcher = mock.patch.object(target, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def get_log(self):
        return self.log_stream.getvalue()

    def assert_password_not_logged(self):
        self.assertNotIn(remote_servers.PASSWORD, self.get_log())

    def connect(self):
        """self.location に self.credentials で接続した Client を返す（テストの終わりに閉じる）"""
        client = remote_storage.connect(self.location, self.credentials)
        self.addCleanup(client.close)
        return client


class ClientOperationsMixin:
    """どの方式でも同じように動くべき、Client の操作のテスト。RemoteTestCase と一緒に継承する"""

    def test_list_dir(self):
        client = self.connect()
        entries = {entry.name: entry for entry in client.list_dir("/")}
        self.assertEqual(set(entries), {"big.bin", JAPANESE_NAME, "folder"})
        self.assertFalse(entries["big.bin"].is_dir)
        self.assertEqual(entries["big.bin"].size, len(BIG_CONTENT))
        self.assertIsNotNone(entries["big.bin"].modified)
        self.assertTrue(entries["folder"].is_dir)
        inner = {entry.name for entry in client.list_dir("/folder")}
        self.assertEqual(inner, {"one.txt", "inner"})

    def test_get_initial_path(self):
        self.assertEqual(self.connect().get_initial_path(), "/")

    def test_get_entry(self):
        client = self.connect()
        entry = client.get_entry("/big.bin")
        self.assertFalse(entry.is_dir)
        self.assertEqual(entry.size, len(BIG_CONTENT))
        self.assertTrue(client.get_entry("/folder").is_dir)

    def test_get_entry_missing(self):
        client = self.connect()
        with self.assertRaises(remote_storage.RemoteError) as context:
            client.get_entry("/missing.txt")
        # 見つからないのは接続の失敗ではない
        self.assertNotIsInstance(context.exception, remote_storage.ConnectError)
        # 接続は続けて使える
        client.check_alive()

    def test_download(self):
        client = self.connect()
        local_path = os.path.join(self.local, "big.bin")
        progress = []
        client.download("/big.bin", local_path, progress.append)
        self.assertEqual(read(local_path), BIG_CONTENT)
        self.assertEqual(sum(progress), len(BIG_CONTENT))

    def test_download_japanese_name(self):
        client = self.connect()
        local_path = os.path.join(self.local, "ja.txt")
        client.download("/" + JAPANESE_NAME, local_path)
        self.assertEqual(read(local_path), "こんにちは".encode("utf-8"))

    def test_download_resume(self):
        client = self.connect()
        local_path = os.path.join(self.local, "big.bin")
        with open(local_path, "wb") as f:
            f.write(BIG_CONTENT[:1000])
        client.download("/big.bin", local_path, offset=1000)
        self.assertEqual(read(local_path), BIG_CONTENT)

    def test_download_canceled_removes_partial_file(self):
        client = self.connect()
        local_path = os.path.join(self.local, "big.bin")

        def cancel(size):
            raise remote_storage.Canceled()

        with self.assertRaises(remote_storage.Canceled):
            client.download("/big.bin", local_path, cancel)
        self.assertFalse(os.path.exists(local_path))

    def test_upload(self):
        client = self.connect()
        local_path = os.path.join(self.local, "up.bin")
        with open(local_path, "wb") as f:
            f.write(BIG_CONTENT)
        progress = []
        client.upload(local_path, "/up.bin", progress.append)
        self.assertEqual(read(os.path.join(self.server_root, "up.bin")), BIG_CONTENT)
        self.assertEqual(sum(progress), len(BIG_CONTENT))

    def test_upload_resume(self):
        client = self.connect()
        local_path = os.path.join(self.local, "up.bin")
        with open(local_path, "wb") as f:
            f.write(BIG_CONTENT)
        with open(os.path.join(self.server_root, "up.bin"), "wb") as f:
            f.write(BIG_CONTENT[:5000])
        client.upload(local_path, "/up.bin", offset=5000)
        self.assertEqual(read(os.path.join(self.server_root, "up.bin")), BIG_CONTENT)

    def test_create_and_remove_file(self):
        client = self.connect()
        client.create_file("/empty.txt")
        self.assertEqual(read(os.path.join(self.server_root, "empty.txt")), b"")
        client.remove_file("/empty.txt")
        self.assertFalse(os.path.exists(os.path.join(self.server_root, "empty.txt")))

    def test_make_and_remove_dir(self):
        client = self.connect()
        client.make_dir("/new")
        self.assertTrue(os.path.isdir(os.path.join(self.server_root, "new")))
        client.remove_dir("/new")
        self.assertFalse(os.path.exists(os.path.join(self.server_root, "new")))

    def test_make_dirs(self):
        client = self.connect()
        client.make_dirs("/a/b/c")
        self.assertTrue(os.path.isdir(os.path.join(self.server_root, "a", "b", "c")))
        # 既にある場合は何もしない
        client.make_dirs("/a/b/c")
        with self.assertRaises(remote_storage.RemoteError):
            client.make_dirs("/big.bin")

    def test_rename(self):
        client = self.connect()
        client.rename("/folder/one.txt", "/moved.txt")
        self.assertEqual(read(os.path.join(self.server_root, "moved.txt")), b"one")
        self.assertFalse(os.path.exists(os.path.join(self.server_root, "folder", "one.txt")))

    def test_set_modified(self):
        client = self.connect()
        modified = datetime.datetime(2020, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)
        self.assertTrue(client.set_modified("/big.bin", modified))
        self.assertEqual(os.path.getmtime(os.path.join(self.server_root, "big.bin")), modified.timestamp())

    def test_remove_missing_file(self):
        client = self.connect()
        with self.assertRaises(remote_storage.RemoteError) as context:
            client.remove_file("/missing.txt")
        self.assertNotIsInstance(context.exception, remote_storage.ConnectError)

    def test_check_alive(self):
        self.connect().check_alive()

    def test_pool_reuses_connection(self):
        remote_storage.credential_store.remember(self.location, self.credentials)
        clients = []
        for dummy in range(2):
            remote_storage.pool.run(self.location, lambda client: clients.append(client))
        self.assertIs(clients[0], clients[1])

    def test_pool_reconnects_dropped_connection(self):
        # サーバーが接続を切った（待ち時間の上限など）後も、つなぎ直して使えること
        remote_storage.credential_store.remember(self.location, self.credentials)
        clients = []
        remote_storage.pool.run(self.location, lambda client: clients.append(client))
        self.server.drop_connections()
        names = remote_storage.pool.run(
            self.location, lambda client: (clients.append(client), [e.name for e in client.list_dir("/")])[1])
        self.assertIn("big.bin", names)
        self.assertIsNot(clients[0], clients[1])

    def test_password_not_logged(self):
        client = self.connect()
        client.list_dir("/")
        self.assert_password_not_logged()
        self.assertIn("connected to %s" % self.location.get_server_key(), self.get_log())

    def test_log_is_english(self):
        # 利用者向けの翻訳された文章をログに書かない（サーバーが返す文章は除く。テストのサーバーは英語）
        client = self.connect()
        with self.assertRaises(remote_storage.RemoteError):
            client.remove_file("/missing.txt")
        with self.assertRaises(remote_storage.RemoteError):
            client.make_dirs("/big.bin")
        remote_storage.credential_store.remember(self.location, self.credentials)
        with self.assertRaises(remote_storage.RemoteError):
            remote_storage.pool.run(self.location, lambda c: c.remove_file("/missing.txt"))
        # ファイル名（日本語のファイル名）以外に、日本語がないこと
        log = self.get_log().replace(JAPANESE_NAME, "")
        self.assertNotRegex(log, "[ぁ-んァ-ヶ一-龠]")


class TransferJobMixin:
    """remote_transfer のジョブのテスト。RemoteTestCase と一緒に継承する"""

    def setUp(self):
        super().setUp()
        remote_storage.credential_store.remember(self.location, self.credentials)

    def run_job(self, job):
        job.start()
        self.assertTrue(job.wait(60), "the job did not finish")
        return job

    def test_download_job(self):
        items = [remote_transfer.DownloadItem("/folder", True), remote_transfer.DownloadItem("/big.bin", False)]
        job = self.run_job(remote_transfer.DownloadJob(remote_transfer.DownloadRequest(self.location, items, self.local)))
        self.assertEqual(job.errors, [])
        self.assertEqual(read(os.path.join(self.local, "big.bin")), BIG_CONTENT)
        self.assertEqual(read(os.path.join(self.local, "folder", "inner", "two.txt")), b"two")
        self.assertEqual(job.percentage, 100)

    def test_download_job_conflict_rename(self):
        with open(os.path.join(self.local, "big.bin"), "wb") as f:
            f.write(b"old")
        items = [remote_transfer.DownloadItem("/big.bin", False)]
        job = self.run_job(remote_transfer.DownloadJob(remote_transfer.DownloadRequest(
            self.location, items, self.local, remote_transfer.CONFLICT_RENAME)))
        self.assertEqual(job.errors, [])
        self.assertEqual(read(os.path.join(self.local, "big.bin")), b"old")
        self.assertEqual(read(os.path.join(self.local, "big (2).bin")), BIG_CONTENT)

    def test_download_job_conflict_skip(self):
        with open(os.path.join(self.local, "big.bin"), "wb") as f:
            f.write(b"old")
        items = [remote_transfer.DownloadItem("/big.bin", False)]
        job = self.run_job(remote_transfer.DownloadJob(remote_transfer.DownloadRequest(
            self.location, items, self.local, remote_transfer.CONFLICT_SKIP)))
        self.assertEqual(read(os.path.join(self.local, "big.bin")), b"old")
        self.assertEqual(len(job.warnings), 1)

    def test_download_job_conflict_resume(self):
        with open(os.path.join(self.local, "big.bin"), "wb") as f:
            f.write(BIG_CONTENT[:12345])
        items = [remote_transfer.DownloadItem("/big.bin", False)]
        job = self.run_job(remote_transfer.DownloadJob(remote_transfer.DownloadRequest(
            self.location, items, self.local, remote_transfer.CONFLICT_RESUME)))
        self.assertEqual(job.errors, [])
        self.assertEqual(read(os.path.join(self.local, "big.bin")), BIG_CONTENT)

    def test_download_job_missing_item(self):
        items = [remote_transfer.DownloadItem("/missing.txt", False), remote_transfer.DownloadItem("/big.bin", False)]
        job = self.run_job(remote_transfer.DownloadJob(remote_transfer.DownloadRequest(self.location, items, self.local)))
        # 見つからない項目はエラーになり、ほかの項目は転送する
        self.assertEqual([target for target, dummy in job.errors], ["/missing.txt"])
        self.assertEqual(read(os.path.join(self.local, "big.bin")), BIG_CONTENT)

    def test_upload_job(self):
        source = os.path.join(self.local, "upfolder")
        os.makedirs(os.path.join(source, "sub"))
        with open(os.path.join(source, "sub", "x.bin"), "wb") as f:
            f.write(BIG_CONTENT)
        single = os.path.join(self.local, "single.txt")
        with open(single, "wb") as f:
            f.write(b"single")
        items = [remote_transfer.UploadItem(source), remote_transfer.UploadItem(single)]
        job = self.run_job(remote_transfer.UploadJob(remote_transfer.UploadRequest(self.location.child("/dest"), items)))
        self.assertEqual(job.errors, [])
        self.assertEqual(read(os.path.join(self.server_root, "dest", "upfolder", "sub", "x.bin")), BIG_CONTENT)
        self.assertEqual(read(os.path.join(self.server_root, "dest", "single.txt")), b"single")

    def test_upload_job_conflict_rename(self):
        local_path = os.path.join(self.local, "big.bin")
        with open(local_path, "wb") as f:
            f.write(b"new")
        job = self.run_job(remote_transfer.UploadJob(remote_transfer.UploadRequest(
            self.location.child("/"), [remote_transfer.UploadItem(local_path)], remote_transfer.CONFLICT_RENAME)))
        self.assertEqual(job.errors, [])
        self.assertEqual(read(os.path.join(self.server_root, "big.bin")), BIG_CONTENT)
        self.assertEqual(read(os.path.join(self.server_root, "big (2).bin")), b"new")

    def test_upload_job_conflict_overwrite(self):
        local_path = os.path.join(self.local, "big.bin")
        with open(local_path, "wb") as f:
            f.write(b"new")
        job = self.run_job(remote_transfer.UploadJob(remote_transfer.UploadRequest(
            self.location.child("/"), [remote_transfer.UploadItem(local_path)], remote_transfer.CONFLICT_OVERWRITE)))
        self.assertEqual(job.errors, [])
        self.assertEqual(read(os.path.join(self.server_root, "big.bin")), b"new")

    def test_delete_job(self):
        items = [remote_transfer.DownloadItem("/folder", True), remote_transfer.DownloadItem("/big.bin", False)]
        job = self.run_job(remote_transfer.DeleteJob(remote_transfer.DeleteRequest(self.location.child("/"), items)))
        self.assertEqual(job.errors, [])
        self.assertEqual(sorted(job.deleted), ["/big.bin", "/folder"])
        self.assertEqual(os.listdir(self.server_root), [JAPANESE_NAME])

    def test_job_cancel(self):
        job = remote_transfer.DownloadJob(remote_transfer.DownloadRequest(
            self.location, [remote_transfer.DownloadItem("/big.bin", False)], self.local))
        job.cancel()
        self.run_job(job)
        self.assertTrue(job.canceled)
