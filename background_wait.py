# -*- coding: utf-8 -*-
# Falcon background wait
# Note: All comments except these top lines will be written in Japanese.

"""
時間がかかることのある処理を別スレッドで実行し、ウィンドウを固めずに終わるのを待つ処理です。

接続が切れたネットワークドライブなどでは、Windowsの関数が数十秒戻ってこないことがあり、途中で止めることもできません。
そのため、利用者が中止したときは、スレッドの終了を待たずに置き去りにします。
別スレッドで実行する処理では、画面の部品や、画面に表示中の一覧を変更してはいけません。
"""

import logging
import threading

import pythoncom

import globalVars
import views.waiting

log = logging.getLogger("falcon.background_wait")

# 処理がこの秒数で終わらないときは、待っていることを示すウィンドウを表示する
_WINDOW_DELAY = 0.3


class Canceled(Exception):
    """利用者が処理を中止した"""


class Task:
    """別スレッドで実行する処理。func には Task 自身と args を渡す。"""

    def __init__(self, func, *args):
        self._func = func
        self._args = args
        self._cancel = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.result = None
        # 失敗したときの例外
        self.error = None

    def start(self):
        """実行を始める"""
        self._thread.start()

    def _run(self):
        # アイコンの取得などのシェルの関数にはCOMの初期化が必要
        pythoncom.CoInitialize()
        try:
            self.result = self._func(self, *self._args)
        except Exception as e:
            self.error = e
        finally:
            pythoncom.CoUninitialize()

    def wait(self, seconds):
        """終わるまで待ち、終わったかどうかを返す"""
        self._thread.join(seconds)
        return self.is_finished()

    def is_finished(self):
        """終わったかどうかを返す"""
        return not self._thread.is_alive()

    def cancel(self):
        """中止を指示する"""
        self._cancel.set()

    def check_canceled(self):
        """(別スレッド)中止を指示されていれば Canceled を投げる"""
        if self._cancel.is_set():
            raise Canceled()


def run(func, *args):
    """
    func(Task, *args) を別スレッドで実行し、終わるまで待って戻り値を返す。メインスレッドから呼ぶこと。
    func が投げた例外はそのまま投げる。利用者が中止した場合は Canceled を投げる。
    """
    task = Task(func, *args)
    task.start()
    if not task.wait(_WINDOW_DELAY):
        # モーダルなので、待っている間に他の操作をされることはない
        globalVars.app.main_window.showSubWindow(views.waiting.WaitingWindow, _("読み込み中"), task)
    if not task.is_finished() or isinstance(task.error, Canceled):
        task.cancel()
        log.info("canceled by the user")
        globalVars.app.say(_("中止しました。"), interrupt=True)
        raise Canceled()
    if task.error is not None:
        raise task.error
    return task.result
