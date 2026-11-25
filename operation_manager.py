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

import archiver
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
    """別スレッドで実行する1つのファイル操作。操作の種類ごとに派生クラスを作る。"""

    def __init__(self, name, directories):
        # 操作の種類の表示名
        self.name = name
        # 終わったときに一覧を更新するフォルダ
        self.directories = directories
        self.title = name
        self.state = WAITING
        # 開始を通知したかどうか
        self.notified = False
        self._started_time = 0
        self._cancel = threading.Event()

    def set_title(self, sources, destination):
        """一覧に表示する内容を、対象のパスのリストと行き先から作る"""
        if len(sources) == 1:
            self.title = _("%(name)s: %(item)s → %(destination)s") % {
                "name": self.name, "item": os.path.basename(sources[0]), "destination": destination}
        else:
            self.title = _("%(name)s: %(count)d項目 → %(destination)s") % {
                "name": self.name, "count": len(sources), "destination": destination}

    def start(self):
        """別スレッドで実行を始める"""
        self.state = RUNNING
        self._started_time = time.monotonic()
        self._start_thread()

    def _start_thread(self):
        raise NotImplementedError

    def is_thread_alive(self):
        """別スレッドの処理が続いているかどうかを返す"""
        raise NotImplementedError

    def join(self, seconds):
        """別スレッドの処理が終わるのを待つ"""
        raise NotImplementedError

    def get_percentage(self):
        """進み具合を返す。まだわからない場合は None"""
        raise NotImplementedError

    def get_details(self):
        """確認が必要な項目を除く、エラーなどの詳細を (対象, 種類, 内容) のリストで返す。実行中は呼ばないこと。"""
        raise NotImplementedError

    def _get_result_state(self):
        """実行を終えた後の状態を返す"""
        raise NotImplementedError

    def prepare_resume(self):
        """利用者の応答を反映し、もう一度実行する必要があるかどうかを返す"""
        return False

    def cancel(self):
        """中止を指示する。実行中の場合、実際に止まるのは少し後。"""
        self._cancel.set()
        if self.state != RUNNING:
            self.state = CANCELED

    def is_canceled(self):
        """中止を指示されたかどうかを返す"""
        return self._cancel.is_set()

    def is_long(self):
        """開始から一定の時間がたったかどうかを返す"""
        return time.monotonic() - self._started_time >= _NOTIFY_DELAY

    def is_unfinished(self):
        """実行中や確認待ちなど、まだ続きがあるかどうかを返す"""
        return self.state in (WAITING, RUNNING, CONFIRMING)

    def has_detail(self):
        """詳細に表示する内容があるかどうかを返す"""
        # 実行中は、別スレッドが内容を変更しているため表示できない
        if self.state in (WAITING, RUNNING):
            return False
        return self.state == CONFIRMING or bool(self.get_details())

    def update_result_state(self):
        """実行を終えた後の状態を決める"""
        self.state = self._get_result_state()

    def get_state_string(self):
        """状態の表示名を返す"""
        if self.state == RUNNING and self.is_canceled():
            return _("中止しています")
        return {
            WAITING: _("待機中"), RUNNING: _("実行中"), CONFIRMING: _("確認待ち"),
            FINISHED: _("完了"), FAILED: _("エラー"), CANCELED: _("中止")}[self.state]

    def get_finish_message(self):
        """実行が終わったときに読み上げる文章を返す"""
        messages = {
            CONFIRMING: _("%(name)sの確認が必要です。"), FAILED: _("%(name)sでエラーが発生しました。"),
            CANCELED: _("%(name)sを中止しました。"), FINISHED: _("%(name)sが完了しました。")}
        return messages[self.state] % {"name": self.name}


class PasteOperation(Operation):
    """コピーまたは移動。FileOperator を実行する。"""

    def __init__(self, operator):
        # 処理が終わると instructions の内容は消えるため、先に求めておく
        instructions = operator.instructions
        sources = [source for source, dummy in instructions["target"]]
        directories = {os.path.dirname(source) for source in sources}
        directories.add(instructions["to"])
        name = _("移動") if instructions["copy_move_flag"] == clipboard.MOVE else _("コピー")
        super().__init__(name, directories)
        self.set_title(sources, instructions["to"])
        self.operator = operator
        # 処理そのものが例外で終わったときの内容
        self._error = None
        self._thread = None

    def _start_thread(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        # 管理者権限への昇格に使うシェルの関数には、COMの初期化が必要
        pythoncom.CoInitialize()
        try:
            self.operator.Execute()
        except Exception as e:
            log.exception("file operation failed")
            self._error = str(e)
        finally:
            self.operator.working = False
            pythoncom.CoUninitialize()

    def is_thread_alive(self):
        return self._thread is not None and self._thread.is_alive()

    def join(self, seconds):
        if self._thread is not None:
            self._thread.join(seconds)

    def cancel(self):
        self.operator.cancel()
        super().cancel()

    def get_percentage(self):
        return None if self.operator.is_counting else self.operator.GetPercentage()

    def get_confirmations(self):
        """応答していない確認項目を返す。実行中は呼ばないこと。"""
        return [element for dummy, element in self.operator.GetConfirmationManager().IterateNotResponded()]

    def get_details(self):
        details = [(element.elem, _("エラー"), str(element.msg[1])) for element in self.operator.CheckFailed()]
        if self._error is not None:
            details.append((self.title, _("エラー"), self._error))
        return details

    def _get_result_state(self):
        if self.is_canceled():
            return CANCELED
        if self.get_confirmations():
            return CONFIRMING
        return FAILED if self.get_details() else FINISHED

    def prepare_resume(self):
        self.operator.UpdateConfirmation()
        # 応答していない確認項目が残っている場合は、実行後にまた確認待ちになる
        return bool(self.operator.instructions["target"])

    def get_state_string(self):
        if self.state == CONFIRMING:
            return _("確認待ち %(count)d件") % {"count": len(self.get_confirmations())}
        if self.state == FAILED:
            return _("エラー %(count)d件") % {"count": len(self.get_details())}
        return super().get_state_string()


class ArchiveOperation(Operation):
    """圧縮または解凍。archiver.Job を実行する。"""

    def __init__(self, name, directories):
        super().__init__(name, directories)
        self._job = None

    def _create_job(self):
        """実行する archiver.Job を作る"""
        raise NotImplementedError

    def _start_thread(self):
        self._job = self._create_job()
        self._job.start()

    def is_thread_alive(self):
        return self._job is not None and not self._job.is_finished()

    def join(self, seconds):
        if self._job is not None:
            self._job.wait(seconds)

    def cancel(self):
        if self._job is not None:
            self._job.cancel()
        super().cancel()

    def get_percentage(self):
        return self._job.percentage if self._job is not None else None

    def get_details(self):
        if self._job is None:
            return []
        details = [(self.title, _("注意"), message) for message in self._job.warnings]
        if self._job.error is not None and not isinstance(self._job.error, archiver.Canceled):
            details.append((self.title, _("エラー"), str(self._job.error)))
        return details

    def _get_result_state(self):
        if isinstance(self._job.error, archiver.Canceled):
            return CANCELED
        # 中止の指示が間に合わなかった場合は、終わったものとして扱う
        return FINISHED if self._job.error is None else FAILED

    def get_state_string(self):
        if self.state == FINISHED and self.get_details():
            return _("完了 注意%(count)d件") % {"count": len(self.get_details())}
        return super().get_state_string()

    def get_finish_message(self):
        if self.state == FINISHED and self.get_details():
            return _("%(name)sが完了しました。注意が%(count)d件あります。") % {"name": self.name, "count": len(self.get_details())}
        return super().get_finish_message()


class CompressOperation(ArchiveOperation):
    """圧縮"""

    def __init__(self, request):
        super().__init__(_("圧縮"), {os.path.dirname(request.destination)})
        self.set_title(request.sources, request.destination)
        self._request = request

    def _create_job(self):
        return archiver.Job(archiver.compress, self._request)


class ExtractOperation(ArchiveOperation):
    """1つの書庫の解凍"""

    def __init__(self, path, request):
        super().__init__(_("解凍"), {request.directory})
        self.set_title([path], request.directory)
        self.path = path
        self._request = request
        # 作る場所は最初に実行するときに決める。先に待っている操作が、同じ名前のファイルを作ることがあるため
        self._directory = None
        self._password = ""

    def _create_job(self):
        if self._directory is None:
            self._directory = self._request.get_directory(self.path)
            self.directories.add(self._directory)
        password, self._password = self._password, ""
        return archiver.Job(archiver.extract, self.path, self._directory, self._request.conflict, password)

    def get_password_message(self):
        """パスワードの入力を求める理由を返す"""
        return "%s\n%s" % (os.path.basename(self.path), self._job.error)

    def set_password(self, password):
        """次の実行で使うパスワードを設定する"""
        self._password = password

    def _get_result_state(self):
        if isinstance(self._job.error, archiver.PasswordError):
            return CANCELED if self.is_canceled() else CONFIRMING
        return super()._get_result_state()

    def prepare_resume(self):
        return self._password != ""

    def get_state_string(self):
        if self.state == CONFIRMING:
            return _("パスワードの入力待ち")
        return super().get_state_string()

    def get_finish_message(self):
        if self.state == CONFIRMING:
            return _("%(name)sにパスワードの入力が必要です。") % {"name": self.name}
        return super().get_finish_message()


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

    def add(self, operation):
        """操作を加える。実行中の操作がなければ、すぐに始める。"""
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
        if operation.is_unfinished():
            operation.cancel()

    def resume(self, operation):
        """確認への応答を反映し、必要ならもう一度実行する。"""
        if operation.state != CONFIRMING:
            return
        if operation.prepare_resume():
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
            if operation.is_unfinished():
                operation.cancel()
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
        self._messages.append(operation.get_finish_message())
        # ダイアログを開いている間などは一覧を更新できないので、先に知らせる
        if not self._main_window.can_update_in_background():
            self._flush_messages()
