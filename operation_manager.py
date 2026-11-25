# -*- coding: utf-8 -*-
# Falcon operation manager
# Note: All comments except these top lines will be written in Japanese.

"""
時間のかかるファイル操作を、別スレッドで1つずつ順番に実行する処理です。
メインスレッドのタイマーで状態を調べ、プログレスバーと一覧の更新、読み上げによる通知を行います。
"""

import logging
import os
import threading
import time

import pythoncom
import wx

import clipboard
import globalVars

log = logging.getLogger("falcon.operation_manager")

# 操作の状態
WAITING = "waiting"
RUNNING = "running"
CONFIRMING = "confirming"
FINISHED = "finished"
FAILED = "failed"
CANCELED = "canceled"

# 状態を調べる間隔(ミリ秒)
_INTERVAL = 100
# 操作がこの秒数で終わらないときは、開始の通知とプログレスバーの表示をする
_NOTIFY_DELAY = 0.3
# falcon の終了時に、中止した操作が止まるのを待つ秒数
_SHUTDOWN_TIMEOUT = 5


class Operation:
    """1つのコピーまたは移動。FileOperator を別スレッドで実行する。"""

    def __init__(self, operator):
        self.operator = operator
        self.state = WAITING
        # 処理そのものが例外で終わったときの内容
        self.error = None
        # 開始を通知したかどうか
        self.notified = False
        self._thread = None
        self._started_time = 0
        # 処理が終わると instructions の内容は消えるため、先に求めておく
        instructions = operator.instructions
        targets = instructions["target"]
        self.directories = {os.path.dirname(source) for source, dummy in targets}
        self.directories.add(instructions["to"])
        self.name = _("移動") if instructions["copy_move_flag"] == clipboard.MOVE else _("コピー")
        destination = instructions["to"]
        if len(targets) == 1:
            self.title = _("%(name)s: %(item)s → %(destination)s") % {
                "name": self.name, "item": os.path.basename(targets[0][0]), "destination": destination}
        else:
            self.title = _("%(name)s: %(count)d項目 → %(destination)s") % {
                "name": self.name, "count": len(targets), "destination": destination}

    def start(self):
        """別スレッドで実行を始める"""
        self.state = RUNNING
        self._started_time = time.monotonic()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        # 管理者権限への昇格に使うシェルの関数には、COMの初期化が必要
        pythoncom.CoInitialize()
        try:
            self.operator.Execute()
        except Exception as e:
            log.exception("file operation failed")
            self.error = str(e)
        finally:
            self.operator.working = False
            pythoncom.CoUninitialize()

    def is_thread_alive(self):
        """別スレッドの処理が続いているかどうかを返す"""
        return self._thread is not None and self._thread.is_alive()

    def join(self, seconds):
        """別スレッドの処理が終わるのを待つ"""
        if self._thread is not None:
            self._thread.join(seconds)

    def is_long(self):
        """開始から一定の時間がたったかどうかを返す"""
        return time.monotonic() - self._started_time >= _NOTIFY_DELAY

    def get_percentage(self):
        """進み具合を返す。まだわからない場合は None"""
        return None if self.operator.is_counting else self.operator.GetPercentage()

    def get_confirmations(self):
        """応答していない確認項目を返す。実行中は呼ばないこと。"""
        return [element for dummy, element in self.operator.GetConfirmationManager().IterateNotResponded()]

    def get_failed(self):
        """処理できなかった項目を返す。実行中は呼ばないこと。"""
        return self.operator.CheckFailed()

    def is_unfinished(self):
        """実行中や確認待ちなど、まだ続きがあるかどうかを返す"""
        return self.state in (WAITING, RUNNING, CONFIRMING)

    def update_result_state(self):
        """実行を終えた後の状態を決める"""
        if self.operator.is_canceled():
            self.state = CANCELED
        elif self.get_confirmations():
            self.state = CONFIRMING
        elif self.error is not None or self.get_failed():
            self.state = FAILED
        else:
            self.state = FINISHED

    def get_state_string(self):
        """状態の表示名を返す"""
        if self.state == RUNNING and self.operator.is_canceled():
            return _("中止しています")
        if self.state == CONFIRMING:
            return _("確認待ち %(count)d件") % {"count": len(self.get_confirmations())}
        if self.state == FAILED:
            if self.get_failed():
                return _("エラー %(count)d件") % {"count": len(self.get_failed())}
            return _("エラー")
        return {WAITING: _("待機中"), RUNNING: _("実行中"), FINISHED: _("完了"), CANCELED: _("中止")}[self.state]


class OperationManager:
    """ファイル操作の一覧を持ち、1つずつ順番に実行する。メソッドはメインスレッドから呼ぶこと。"""

    def __init__(self, main_window):
        self.operations = []
        self._main_window = main_window
        # 更新が必要なフォルダ
        self._directories = set()
        self._messages = []
        self._timer = wx.Timer(main_window)
        main_window.Bind(wx.EVT_TIMER, self._on_timer, self._timer)

    def add(self, operator):
        """操作を加える。実行中の操作がなければ、すぐに始める。"""
        operation = Operation(operator)
        self.operations.append(operation)
        if self.get_running() is not None:
            self._say(_("%(name)sを待機中に追加しました。") % {"name": operation.name})
        self._start_next()

    def get_running(self):
        """実行中の操作を返す。なければ None"""
        for operation in self.operations:
            if operation.state == RUNNING:
                return operation
        return None

    def get_unfinished_count(self):
        """終わっていない操作の数を返す"""
        return sum(operation.is_unfinished() for operation in self.operations)

    def cancel(self, operation):
        """操作を中止する。実行中の場合、実際に止まるのは少し後。"""
        if not operation.is_unfinished():
            return
        operation.operator.cancel()
        if operation.state != RUNNING:
            operation.state = CANCELED

    def resume(self, operation):
        """確認項目への応答を反映し、必要ならもう一度実行する。"""
        if operation.state != CONFIRMING:
            return
        operation.operator.UpdateConfirmation()
        if operation.operator.instructions["target"]:
            # 応答していない確認項目が残っている場合は、実行後にまた確認待ちになる
            operation.state = WAITING
            operation.notified = False
            self._start_next()
        else:
            operation.update_result_state()

    def remove_finished(self):
        """終わった操作を一覧から消す"""
        self.operations = [operation for operation in self.operations if operation.is_unfinished()]

    def say_progress(self):
        """実行中の操作の進み具合と、確認待ちの件数を読み上げる"""
        messages = []
        running = self.get_running()
        if running is not None:
            percentage = running.get_percentage()
            messages.append(running.title)
            messages.append(running.get_state_string() if percentage is None else _("%(percentage)d%%") % {"percentage": percentage})
        waiting = sum(operation.state == WAITING for operation in self.operations)
        if waiting:
            messages.append(_("待機中 %(count)d件") % {"count": waiting})
        confirming = sum(operation.state == CONFIRMING for operation in self.operations)
        if confirming:
            messages.append(_("確認待ちの操作 %(count)d件") % {"count": confirming})
        self._say(" ".join(messages) if messages else _("実行中のファイル操作はありません。"), True)

    def update_gauge(self):
        """メインウィンドウのプログレスバーに、進み具合を反映する"""
        running = self.get_running()
        self._main_window.set_progress(running.get_percentage() if running is not None and running.is_long() else None)

    def shutdown(self):
        """全ての操作を中止し、止まるのを待つ。falcon の終了時に呼ぶ。"""
        self._timer.Stop()
        for operation in self.operations:
            operation.operator.cancel()
        running = self.get_running()
        if running is not None:
            running.join(_SHUTDOWN_TIMEOUT)

    def _say(self, message, interrupt=False):
        globalVars.app.say(message, interrupt=interrupt)

    def _start_next(self):
        """実行中の操作がなければ、待機中の操作を始める"""
        if self.get_running() is None:
            for operation in self.operations:
                if operation.state == WAITING:
                    operation.start()
                    break
        if not self._timer.IsRunning():
            self._timer.Start(_INTERVAL)

    def _on_timer(self, event):
        running = self.get_running()
        if running is not None:
            if not running.is_thread_alive():
                self._on_finish(running)
                self._start_next()
            elif running.is_long() and not running.notified:
                running.notified = True
                self._say(_("%(name)sを開始しました。") % {"name": running.name})
        self.update_gauge()
        if self._directories and self._main_window.can_update_in_background():
            directories, self._directories = self._directories, set()
            # ネットワーク上のフォルダでは読み込み中のウィンドウが出て、その間もタイマーが動くことがある
            self._main_window.refresh_file_lists(directories)
        # 一覧の更新による読み上げに消されないよう、更新の後に知らせる
        if self._messages and not self._directories:
            self._flush_messages()
        if self.get_running() is None and not self._directories and not self._main_window.progress_gauge.IsShown():
            self._timer.Stop()

    def _flush_messages(self):
        messages, self._messages = self._messages, []
        self._say(" ".join(messages))

    def _on_finish(self, operation):
        """操作が終わったときの処理"""
        operation.update_result_state()
        self._directories |= operation.directories
        name = {"name": operation.name}
        if operation.state == CONFIRMING:
            message = _("%(name)sの確認が必要です。") % name
        elif operation.state == FAILED:
            message = _("%(name)sでエラーが発生しました。") % name
        elif operation.state == CANCELED:
            message = _("%(name)sを中止しました。") % name
        else:
            message = _("%(name)sが完了しました。") % name
        self._messages.append(message)
        # ダイアログを開いている間などは一覧を更新できないので、先に知らせる
        if not self._main_window.can_update_in_background():
            self._flush_messages()
