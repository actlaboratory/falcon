# -*- coding: utf-8 -*-
# Falcon remote credential store tests
# Note: All comments except these top lines will be written in Japanese.

"""資格情報の保管場所（remote_storage.CredentialStore）のテストです。サーバーには接続しません。"""

import unittest

import remote_servers

remote_servers.setup_falcon_path()

import remote_storage  # noqa: E402


class TestCredentialStore(unittest.TestCase):
    """同じサーバーの、ユーザーごとの資格情報"""

    def setUp(self):
        self.store = remote_storage.CredentialStore()
        # PC の資格情報マネージャーは使わない
        self.saved = {}
        self.store._read_windows = lambda key: self.saved.get(key)

    def location(self, user):
        return remote_storage.Location(remote_storage.SCHEME_SFTP, "example.com", 22, user, "/")

    def test_users_are_separated(self):
        self.store.remember(self.location("alice"), remote_storage.Credentials("alice", "a"))
        self.store.remember(self.location("bob"), remote_storage.Credentials("bob", "b"))
        self.assertEqual(self.store.get(self.location("alice")).password, "a")
        self.assertEqual(self.store.get(self.location("bob")).password, "b")

    def test_forget_keeps_other_user(self):
        self.store.remember(self.location("alice"), remote_storage.Credentials("alice", "a"))
        self.store.remember(self.location("bob"), remote_storage.Credentials("bob", "b"))
        self.store.forget(self.location("alice"))
        self.assertIsNone(self.store.get(self.location("alice")))
        self.assertEqual(self.store.get(self.location("bob")).password, "b")

    def test_remembered_without_user_in_url(self):
        # ユーザー名のない URL で入力した資格情報は、同じユーザー名の URL でも使う
        self.store.remember(self.location(""), remote_storage.Credentials("alice", "a"))
        self.assertEqual(self.store.get(self.location("")).user, "alice")
        self.assertEqual(self.store.get(self.location("alice")).password, "a")
        self.assertIsNone(self.store.get(self.location("bob")))

    def test_saved_by_older_version(self):
        # 以前の版は、ユーザー名を含まない key で資格情報マネージャーに保存していた
        self.saved["sftp://example.com:22"] = remote_storage.Credentials("alice", "a")
        self.assertEqual(self.store.get(self.location("alice")).password, "a")
        self.assertIsNone(self.store.get(self.location("bob")))

    def test_account_key(self):
        self.assertEqual(self.location("").get_account_key(), "sftp://example.com:22")
        self.assertEqual(self.location("a@b").get_account_key(), "sftp://a%40b@example.com:22")


if __name__ == "__main__":
    unittest.main()
