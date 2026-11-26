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
                raise background_wait.Canceled()
        except remote_storage.UnknownHostKey as err:
            if not _confirm_host_key(location, err):
                raise background_wait.Canceled()
            remote_storage.add_known_host(err)
        except remote_storage.UntrustedCertificate as err:
            if not _confirm_certificate(location, err):
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
    remote_storage.set_proxy(get_proxy() if settings.get_bool("remote", "use_proxy", False) else None)


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
        "%(host)s に初めて接続します。\n"
        "サーバーの鍵の指紋: %(fingerprint)s\n\n"
        "接続先がこのサーバーで間違いなければ「はい」を選んでください。鍵を保存して接続します。\n"
        "次からは、鍵が変わっていた場合に警告します。") % {"host": location.get_display_host(), "fingerprint": err.get_fingerprint()}
    return _ask_yes_no(_("サーバーの確認"), message)


def _confirm_certificate(location, err):
    """
    検証できない FTPS の証明書で接続するかどうかを、指紋を見せて確認してもらう。
    許可した証明書だけを、次からも使う（違う証明書なら、また確認する）。
    """
    if not err.fingerprint:
        dialog(_("エラー"), _("%(error)s\n\n証明書を取り出せなかったため、接続できません。") % {"error": err})
        return False
    details = ("\n" + err.details) if err.details else ""
    if err.changed:
        message = _(
            "%(error)s\n\n"
            "新しい証明書の指紋: %(fingerprint)s%(details)s\n\n"
            "サーバーの管理者が証明書を更新した場合を除き、接続しないでください。\n"
            "この新しい証明書を許可して接続しますか？") % {"error": err, "fingerprint": err.fingerprint, "details": details}
    else:
        message = _(
            "%(error)s\n\n"
            "証明書の指紋: %(fingerprint)s%(details)s\n\n"
            "自分で作った証明書を使っている機器（NASなど）では、この表示が出ることがあります。\n"
            "指紋が機器の設定画面などに表示されているものと同じであれば、接続先は本物です。\n"
            "この証明書を許可して接続しますか？許可した証明書は保存し、次からは違う証明書の場合だけ確認します。") % {
            "error": err, "fingerprint": err.fingerprint, "details": details}
    return _ask_yes_no(_("証明書の確認"), message)


def _ask_yes_no(title, message):
    dlg = wx.MessageDialog(globalVars.app.main_window, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
    result = dlg.ShowModal()
    dlg.Destroy()
    return result == wx.ID_YES
