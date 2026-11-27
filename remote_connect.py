# -*- coding: utf-8 -*-
# Falcon remote connect
# Note: All comments except these top lines will be written in Japanese.

"""
FTP・SFTP のサーバーへの操作を、ウィンドウを固めずに実行する処理です。メインスレッドから使います。
ユーザー名とパスワードの入力、SFTP のホスト鍵の確認、FTPS の証明書の確認が必要になったときは、
ここで画面を出して、入力された内容で操作をやり直します。
SFTP の鍵ファイルとプロキシの設定は、falcon の設定から読んで remote_storage に渡します。
"""

import logging
import os
import urllib.parse

import wx

import background_wait
import globalVars
import remote_storage
import views.remote_login

from simpleDialog import dialog

log = logging.getLogger("falcon.remote_connect")

# SFTP の鍵ファイルを保存する設定のセクション（サーバーの key -> パス）
KEY_FILE_SECTION = "remote_key_files"

# 最後にログに書いたプロキシの設定（(使うかどうか, プロキシ)）
_logged_proxy = [None]


def run(location, func, *args, pass_task=False):
    """
    func(client, *args) を別スレッドで実行し、その戻り値を返す。client は remote_storage.Client。
    pass_task=True の場合は func(client, task, *args) として、中止を調べるための background_wait.Task も渡す。
    利用者が中止した場合や、資格情報の入力をやめた場合は background_wait.Canceled になる。
    それ以外の失敗は remote_storage.RemoteError になる（呼び出し側で利用者に知らせる）。
    """
    apply_settings()
    while True:
        try:
            return background_wait.run(_run, location, func, args, pass_task)
        except remote_storage.AuthRequired as err:
            # 保存していたパスワードが違っていた場合に、次から使わないようにする
            remote_storage.credential_store.forget(location)
            if not ask_login(location, str(err)):
                log.info("login to %s canceled by the user" % location.get_server_key())
                raise background_wait.Canceled()
        except remote_storage.UnknownHostKey as err:
            if not _confirm_host_key(location, err):
                log.info("the host key of %s rejected by the user: %s" % (location.get_server_key(), err.get_fingerprint()))
                raise background_wait.Canceled()
            remote_storage.add_known_host(err)
        except remote_storage.UntrustedCertificate as err:
            if not _confirm_certificate(location, err):
                log.info("the certificate of %s rejected by the user: %s (changed: %s)" % (
                    location.get_server_key(), err.fingerprint or "-", err.changed))
                raise background_wait.Canceled()
            remote_storage.certificate_trust.trust(location, err.fingerprint)


def _run(task, location, func, args, pass_task):
    """(別スレッド)接続を使い回して func を呼ぶ"""
    if pass_task:
        args = (task,) + tuple(args)
    return remote_storage.pool.run(location, func, *args)


def apply_settings():
    """falcon の設定（SFTP の鍵ファイル、プロキシ）を remote_storage に反映する。転送を始める前にも呼ぶ"""
    settings = globalVars.app.settings
    remote_storage.credential_store.set_key_files(settings.get_section(KEY_FILE_SECTION) or {})
    use_proxy = settings.get_bool("remote", "use_proxy", False)
    proxy = get_proxy() if use_proxy else None
    if (use_proxy, proxy) != _logged_proxy[0]:
        # 操作のたびに呼ばれるので、変わったときだけログに書く
        _logged_proxy[0] = (use_proxy, proxy)
        if use_proxy and proxy is None:
            log.warning("remote.use_proxy is enabled, but no proxy is found. connect directly")
        else:
            log.info("proxy for FTP/SFTP: %s" % ("%s:%d" % proxy if proxy is not None else "none"))
    remote_storage.set_proxy(proxy)


def get_proxy():
    """
    falcon が使っている HTTP プロキシ（設定で手動で指定したもの、または Windows の設定から見つけたもの）を
    (サーバー, ポート) で返す。ない場合は None
    """
    text = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or ""
    text = text.strip()
    if not text:
        return None
    # Windows の設定は「http=サーバー:ポート;https=サーバー:ポート」の形のことがある
    if "=" in text:
        entries = dict(part.split("=", 1) for part in text.split(";") if "=" in part)
        text = entries.get("https") or entries.get("http") or ""
    if "://" not in text:
        text = "http://" + text
    try:
        parsed = urllib.parse.urlsplit(text)
        if not parsed.hostname:
            return None
        return parsed.hostname, parsed.port or 8080
    except ValueError:
        log.warning("Cannot parse the proxy setting: %s" % text)
        return None


def ask_login(location, message):
    """ユーザー名とパスワード（SFTP では鍵ファイルも）を入力してもらい、覚える。入力をやめた場合は False を返す"""
    stored = remote_storage.credential_store.get(location)
    user = location.user or (stored.user if stored is not None else "")
    parameters = views.remote_login.RemoteLoginParameters(
        "%s\n%s" % (location.get_url(path="", with_user=False), message), user, user_editable=not location.user,
        insecure=location.scheme == remote_storage.SCHEME_FTP,
        use_key_file=location.scheme == remote_storage.SCHEME_SFTP,
        key_file=remote_storage.credential_store.get_key_file(location))
    result = globalVars.app.main_window.showSubWindow(views.remote_login.RemoteLoginWindow, _("ログイン"), parameters)
    if getattr(result, "code", wx.ID_CANCEL) == wx.ID_CANCEL:
        return False
    credentials = result.user_object.credentials
    if location.scheme == remote_storage.SCHEME_SFTP:
        _save_key_file(location, credentials.key_file)
    remote_storage.credential_store.remember(location, credentials, result.user_object.save)
    return True


def _save_key_file(location, key_file):
    """鍵ファイルのパスを falcon の設定に保存する。空なら消す"""
    settings = globalVars.app.settings
    key_files = dict(settings.get_section(KEY_FILE_SECTION) or {})
    key = location.get_server_key()
    if key_file:
        key_files[key] = key_file
    else:
        key_files.pop(key, None)
    settings.replace_section(KEY_FILE_SECTION, key_files)
    globalVars.app.save_settings()
    remote_storage.credential_store.set_key_files(key_files)


def _confirm_host_key(location, err):
    """初めて接続する SFTP サーバーの鍵を確認してもらう"""
    message = _(
        "%(host)s のホスト鍵は未登録です。\n"
        "フィンガープリント: %(fingerprint)s\n\n"
        "このホスト鍵を信頼して接続しますか？（known_hosts に保存されます）") % {"host": location.get_display_host(), "fingerprint": err.get_fingerprint()}
    return _ask_yes_no(_("ホスト鍵の確認"), message)


def _confirm_certificate(location, err):
    """
    検証できない FTPS の証明書で接続するかどうかを、指紋を見せて確認してもらう。
    許可した証明書だけを、次からも使う（違う証明書なら、また確認する）。
    """
    if not err.fingerprint:
        dialog(_("エラー"), _("%(error)s\n\n証明書を取得できないため、接続を中止しました。") % {"error": err})
        return False
    details = ("\n" + err.details) if err.details else ""
    if err.changed:
        message = _(
            "%(error)s\n\n"
            "新しい証明書のフィンガープリント: %(fingerprint)s%(details)s\n\n"
            "証明書の更新が確認できない場合は、接続しないでください。\n"
            "この証明書を信頼して接続しますか？") % {"error": err, "fingerprint": err.fingerprint, "details": details}
    else:
        message = _(
            "%(error)s\n\n"
            "フィンガープリント: %(fingerprint)s%(details)s\n\n"
            "自己署名証明書の場合は、サーバー側に表示されるフィンガープリントと一致することを確認してください。\n"
            "この証明書を信頼して接続しますか？（信頼した証明書は保存されます）") % {
            "error": err, "fingerprint": err.fingerprint, "details": details}
    return _ask_yes_no(_("証明書の確認"), message)


def _ask_yes_no(title, message):
    dlg = wx.MessageDialog(globalVars.app.main_window, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
    result = dlg.ShowModal()
    dlg.Destroy()
    return result == wx.ID_YES
