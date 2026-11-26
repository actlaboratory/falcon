# -*- coding: utf-8 -*-
# Falcon remote connect
# Note: All comments except these top lines will be written in Japanese.

"""
FTP・SFTP のサーバーへの操作を、ウィンドウを固めずに実行する処理です。メインスレッドから使います。
ユーザー名とパスワードの入力、SFTP のホスト鍵の確認、FTPS の証明書の確認が必要になったときは、
ここで画面を出して、入力された内容で操作をやり直します。
"""

import logging

import wx

import background_wait
import globalVars
import remote_storage
import views.remote_login

log = logging.getLogger("falcon.remote_connect")


def run(location, func, *args, pass_task=False):
    """
    func(client, *args) を別スレッドで実行し、その戻り値を返す。client は remote_storage.Client。
    pass_task=True の場合は func(client, task, *args) として、中止を調べるための background_wait.Task も渡す。
    利用者が中止した場合や、資格情報の入力をやめた場合は background_wait.Canceled になる。
    それ以外の失敗は remote_storage.RemoteError になる（呼び出し側で利用者に知らせる）。
    """
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
            remote_storage.certificate_trust.trust(location)


def _run(task, location, func, args, pass_task):
    """(別スレッド)接続を使い回して func を呼ぶ"""
    if pass_task:
        args = (task,) + tuple(args)
    return remote_storage.pool.run(location, func, *args)


def ask_login(location, message):
    """ユーザー名とパスワードを入力してもらい、覚える。入力をやめた場合は False を返す"""
    stored = remote_storage.credential_store.get(location)
    user = location.user or (stored.user if stored is not None else "")
    parameters = views.remote_login.RemoteLoginParameters(
        "%s\n%s" % (location.get_url(path="", with_user=False), message), user, user_editable=not location.user)
    result = globalVars.app.main_window.showSubWindow(views.remote_login.RemoteLoginWindow, _("ログイン"), parameters)
    if getattr(result, "code", wx.ID_CANCEL) == wx.ID_CANCEL:
        return False
    remote_storage.credential_store.remember(location, result.user_object.credentials, result.user_object.save)
    return True


def _confirm_host_key(location, err):
    """初めて接続する SFTP サーバーの鍵を確認してもらう"""
    message = _(
        "%(host)s に初めて接続します。\n"
        "サーバーの鍵の指紋: %(fingerprint)s\n\n"
        "接続先がこのサーバーで間違いなければ「はい」を選んでください。鍵を保存して接続します。\n"
        "次からは、鍵が変わっていた場合に警告します。") % {"host": location.get_display_host(), "fingerprint": err.get_fingerprint()}
    return _ask_yes_no(_("サーバーの確認"), message)


def _confirm_certificate(location, err):
    """検証できない FTPS の証明書で接続するかどうかを確認してもらう"""
    message = _(
        "%(error)s\n\n"
        "自分で作った証明書を使っている機器（NASなど）では、この表示が出ることがあります。\n"
        "通信は暗号化されますが、接続先が本物かどうかは確認できません。接続しますか？") % {"error": err}
    return _ask_yes_no(_("証明書の確認"), message)


def _ask_yes_no(title, message):
    dlg = wx.MessageDialog(globalVars.app.main_window, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
    result = dlg.ShowModal()
    dlg.Destroy()
    return result == wx.ID_YES
