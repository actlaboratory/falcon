# -*- coding: utf-8 -*-
# Falcon operation manager
# Note: All comments except these top lines will be written in Japanese.

"""
時間のかかるファイル操作を、別スレッドで順番に実行する処理です。
コピー・移動・圧縮・解凍は1つずつ実行します。完全削除とゴミ箱への移動は、待っている間に同じ場所に
作られた別のファイルを消さないよう、場所が重なる操作がなければ待たずに始めます。
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
import fileOperator
import globalVars
import operation_result
import remote_transfer
import reparse_link
from fileOperator import helper

log = logging.getLogger("falcon.operation_manager")

# 操作の状態
WAITING = "waiting"
RUNNING = "running"
CONFIRMING = "confirming"
FINISHED = "finished"
FAILED = "failed"
CANCELED = "canceled"

# 同時に実行しない操作の組
_LANE_MAIN = "main"
_LANE_DELETE = "delete"

# 状態を調べる間隔(ミリ秒)
_INTERVAL = 100
# 操作がこの秒数で終わらないときは、開始の通知とプログレスバーの表示をする
_NOTIFY_DELAY = 0.3
# falcon の終了時に、中止した操作が止まるのを待つ秒数
_SHUTDOWN_TIMEOUT = 5


class Operation:
    """別スレッドで実行する1つのファイル操作。操作の種類ごとに派生クラスを作る。"""

    lane = _LANE_MAIN

    def __init__(self, name, directories, paths):
        # 操作の種類の表示名
        self.name = name
        # 終わったときに一覧を更新するフォルダ
        self.directories = directories
        # 読み書きするパス。場所が重なる操作を同時に実行しないために使う
        self._paths = [os.path.join(os.path.normcase(path), "") for path in paths]
        # 削除・移動によって元の場所からなくなるパス。終わったときに検索結果の一覧から取り除く
        self.deleted_paths = []
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

    def overlaps(self, other):
        """other と、読み書きする場所が重なるかどうかを返す"""
        return any(a.startswith(b) or b.startswith(a) for a in self._paths for b in other._paths)

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


class FileOperatorOperation(Operation):
    """FileOperator を実行する操作"""

    def __init__(self, name, directories, paths, operator):
        super().__init__(name, directories, paths)
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
        details = [(element.elem, _("エラー"), operation_result.get_error_message(element)) for element in self.operator.CheckFailed()]
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


class PasteOperation(FileOperatorOperation):
    """コピーまたは移動"""

    def __init__(self, operator):
        # 処理が終わると instructions の内容は消えるため、先に求めておく
        instructions = operator.instructions
        sources = [source for source, dummy in instructions["target"]]
        directories = {os.path.dirname(source) for source in sources}
        directories.add(instructions["to"])
        name = _("移動") if instructions["copy_move_flag"] == clipboard.MOVE else _("コピー")
        paths = sources + [destination for dummy, destination in instructions["target"]]
        super().__init__(name, directories, paths, operator)
        if instructions["copy_move_flag"] == clipboard.MOVE:
            self.deleted_paths = sources
        self.set_title(sources, instructions["to"])


class DeleteOperation(FileOperatorOperation):
    """完全削除またはゴミ箱への移動"""

    lane = _LANE_DELETE

    def __init__(self, operator):
        targets = list(operator.instructions["target"])
        name = _("ゴミ箱への移動") if operator.instructions["operation"] == "trash" else _("完全削除")
        super().__init__(name, {os.path.dirname(target) for target in targets}, targets, operator)
        self.deleted_paths = targets
        self._set_delete_title(targets)
        # ゴミ箱を使えない場所のため、削除しなかった項目
        self._unrecyclable = []
        # 完全に削除するかどうかを尋ねる文章
        self._question = ""
        self._must_resume = False

    def _set_delete_title(self, targets):
        if len(targets) == 1:
            self.title = _("%(name)s: %(item)s") % {"name": self.name, "item": targets[0]}
        else:
            self.title = _("%(name)s: %(count)d項目 (%(directory)s)") % {
                "name": self.name, "count": len(targets), "directory": os.path.dirname(targets[0])}

    def _run(self):
        super()._run()
        self._unrecyclable = [element for element in self.operator.CheckFailed() if element.msg[1] == helper.NO_RECYCLE_BIN]
        # ネットワーク上の項目を調べるのには時間がかかることがあるので、別スレッドのうちに文章を作る
        if len(self._unrecyclable) == 1:
            path = self._unrecyclable[0].elem
            if reparse_link.is_directory_entry(path):
                self._question = _("%(path)s\nこのフォルダを完全に削除しますか？") % {"path": path}
            else:
                self._question = _("%(path)s\nこのファイルを完全に削除しますか？") % {"path": path}
        else:
            self._question = _("これらの %(count)d個の項目を完全に削除しますか？") % {"count": len(self._unrecyclable)}

    def _get_result_state(self):
        # 中止の指示が間に合わず、すべて削除された場合は、終わったものとして扱う
        if self.is_canceled() and not any(os.path.lexists(path) for path in self.deleted_paths):
            return FINISHED
        if not self.is_canceled() and self._unrecyclable and globalVars.app.settings.get_bool("general", "confirm_unrecyclable", True):
            return CONFIRMING
        return super()._get_result_state()

    def get_question(self):
        """完全に削除するかどうかを尋ねる文章を返す"""
        return self._question

    def answer(self, permanently):
        """完全に削除するかどうかの答えを反映する。削除する場合は、その後に再開する必要がある。"""
        paths = [element.elem for element in self._unrecyclable]
        failed = [element for element in self.operator.CheckFailed() if element not in self._unrecyclable]
        self._unrecyclable = []
        if not permanently:
            self.operator.output["failed"] = failed
            self.state = FAILED if failed else CANCELED
            return
        self.name = _("完全削除")
        self._set_delete_title(paths)
        self.operator = fileOperator.FileOperator({"operation": "delete", "target": paths})
        self.operator.output["failed"] = failed
        self._must_resume = True

    def prepare_resume(self):
        must_resume, self._must_resume = self._must_resume, False
        return must_resume

    def get_state_string(self):
        if self.state == CONFIRMING:
            return _("確認待ち %(count)d件") % {"count": len(self._unrecyclable)}
        return super().get_state_string()

    def get_finish_message(self):
        # 失敗の理由を見なくても、どうすればよいかわかるようにする
        if self.state == FAILED and self._unrecyclable:
            return _("ゴミ箱を使えない場所のため、削除しませんでした。")
        # すぐに終わった削除では、次の項目の読み上げを優先する
        if self.state == FINISHED and not self.notified:
            return ""
        return super().get_finish_message()


class ArchiveOperation(Operation):
    """圧縮または解凍。archiver.Job を実行する。"""

    def __init__(self, name, directories, paths):
        super().__init__(name, directories, paths)
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
        super().__init__(_("圧縮"), {os.path.dirname(request.destination)}, request.sources + [request.destination])
        self.set_title(request.sources, request.destination)
        self._request = request

    def _create_job(self):
        return archiver.Job(archiver.compress, self._request)


class ExtractOperation(ArchiveOperation):
    """1つの書庫の解凍"""

    def __init__(self, path, request):
        super().__init__(_("解凍"), {request.directory}, [path, request.get_directory(path)])
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


class RemoteOperation(Operation):
    """FTP・SFTP のサーバーへの操作。remote_transfer.RemoteJob の派生クラスを実行する。"""

    def __init__(self, name, directories, paths, request):
        super().__init__(name, directories, paths)
        self._request = request
        self._job = None

    def _make_job(self):
        raise NotImplementedError

    def _start_thread(self):
        self._job = self._make_job()
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
        details = [(target, _("注意"), message) for target, message in self._job.warnings]
        details += [(target, _("エラー"), message) for target, message in self._job.errors]
        return details

    def _get_warning_count(self):
        return len(self._job.warnings) if self._job is not None else 0

    def _get_result_state(self):
        if self._job.canceled:
            return CANCELED
        return FAILED if self._job.errors else FINISHED

    def get_state_string(self):
        if self.state == FAILED:
            return _("エラー %(count)d件") % {"count": len(self._job.errors)}
        if self.state == FINISHED and self._get_warning_count():
            return _("完了 注意%(count)d件") % {"count": self._get_warning_count()}
        return super().get_state_string()

    def get_finish_message(self):
        if self.state == FINISHED and self._get_warning_count():
            return _("%(name)sが完了しました。注意が%(count)d件あります。") % {"name": self.name, "count": self._get_warning_count()}
        return super().get_finish_message()


class DownloadOperation(RemoteOperation):
    """FTP・SFTP のサーバーからのダウンロード"""

    def __init__(self, request):
        super().__init__(_("ダウンロード"), {request.directory}, [request.directory], request)
        self.set_title([item.get_name() for item in request.items], request.directory)

    def _make_job(self):
        return remote_transfer.DownloadJob(self._request)


class UploadOperation(RemoteOperation):
    """FTP・SFTP のサーバーへのアップロード。終わったら、アップロード先のフォルダの一覧を更新する"""

    def __init__(self, request):
        url = request.location.get_url()
        super().__init__(_("アップロード"), {url}, [url], request)
        self.set_title([item.local_path for item in request.items], url)

    def _make_job(self):
        return remote_transfer.UploadJob(self._request)


class RemoteDeleteOperation(RemoteOperation):
    """FTP・SFTP のサーバー上の項目の削除。サーバーにはごみ箱がないので、完全に削除する"""

    lane = _LANE_DELETE

    def __init__(self, request):
        url = request.location.get_url()
        super().__init__(_("削除"), {url}, [request.location.get_url(item.path) for item in request.items], request)
        names = [item.get_name() for item in request.items]
        if len(names) == 1:
            self.title = _("%(name)s: %(item)s") % {"name": self.name, "item": names[0]}
        else:
            self.title = _("%(name)s: %(count)d項目") % {"name": self.name, "count": len(names)}

    def _make_job(self):
        return remote_transfer.DeleteJob(self._request)


class OperationManager:
    """ファイル操作の一覧を持ち、順番に実行する。メソッドはメインスレッドから呼ぶこと。"""

    def __init__(self, main_window):
        self.operations = []
        self._main_window = main_window
        # 更新が必要なフォルダ
        self._directories = set()
        self._messages = []
        # 検索結果の一覧から取り除くパス
        self._deleted_paths = []
        # 完全に削除するかどうかを、これから尋ねる操作
        self._questions = []
        self._timer = wx.Timer(main_window)
        main_window.Bind(wx.EVT_TIMER, self._on_timer, self._timer)

    def add(self, operation):
        """操作を加える。待つ必要のある操作がなければ、すぐに始める。"""
        self.operations.append(operation)
        self._start_next()
        if operation.state == WAITING:
            self._say(_("%(name)sを待機中に追加しました。") % {"name": operation.name})

    def get_running_operations(self):
        """実行中の操作のリストを返す"""
        return [operation for operation in self.operations if operation.state == RUNNING]

    def get_running(self):
        """プログレスバーに表示する、実行中の操作を返す。なければ None"""
        running = self.get_running_operations()
        # 進み具合がわかるものを優先する
        for operation in running:
            if operation.get_percentage() is not None:
                return operation
        return running[0] if running else None

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
        for running in self.get_running_operations():
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
        for operation in self.get_running_operations():
            operation.join(_SHUTDOWN_TIMEOUT)

    def _say(self, message, interrupt=False):
        globalVars.app.say(message, interrupt=interrupt)

    def _start_next(self):
        """始められる待機中の操作を始める"""
        blocking = []
        for operation in self.operations:
            if operation.state == WAITING and self._can_start(operation, blocking):
                operation.start()
            if operation.state in (WAITING, RUNNING):
                blocking.append(operation)
        if not self._timer.IsRunning():
            self._timer.Start(_INTERVAL)

    def _can_start(self, operation, earlier):
        """先に加えられた操作と、実行中の操作を待つ必要がないかどうかを返す"""
        return not any(
            (other.state == RUNNING and other.lane == operation.lane) or other.overlaps(operation)
            for other in earlier + self.get_running_operations())

    def _on_timer(self, event):
        for running in self.get_running_operations():
            if not running.is_thread_alive():
                self._on_finish(running)
            elif running.is_long() and not running.notified:
                running.notified = True
                self._say(_("%(name)sを開始しました。") % {"name": running.name})
        self._start_next()
        self.update_gauge()
        if self._directories and self._main_window.can_update_in_background():
            directories, self._directories = self._directories, set()
            deleted_paths, self._deleted_paths = self._deleted_paths, []
            # ネットワーク上のフォルダでは読み込み中のウィンドウが出て、その間もタイマーが動くことがある
            self._main_window.refresh_file_lists(directories, deleted_paths)
        # 一覧の更新による読み上げに消されないよう、更新の後に知らせる
        if self._messages and not self._directories:
            self._flush_messages()
        if self._questions and not self._directories and self._main_window.can_ask():
            self.ask_permanent_delete(self._questions.pop(0))
        if not self.get_running_operations() and not self._directories and not self._questions and not self._main_window.progress_gauge.IsShown():
            self._timer.Stop()

    def ask_permanent_delete(self, operation, parent=None):
        """ゴミ箱を使えない項目を完全に削除するか尋ね、答えに応じて再開する。"""
        # 尋ねる前に、進行状況の一覧で答えたり中止したりしていることがある
        if operation.state != CONFIRMING:
            return
        dlg = wx.MessageDialog(
            parent or self._main_window, operation.get_question(), _("完全削除の確認"),
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
        result = dlg.ShowModal()
        dlg.Destroy()
        if operation.state != CONFIRMING:
            return
        operation.answer(result == wx.ID_YES)
        self.resume(operation)

    def _flush_messages(self):
        messages, self._messages = self._messages, []
        if messages:
            self._say(" ".join(messages))

    def _on_finish(self, operation):
        """操作が終わったときの処理"""
        operation.update_result_state()
        self._directories |= operation.directories
        self._deleted_paths += operation.deleted_paths
        if isinstance(operation, DeleteOperation):
            if operation.state == CONFIRMING:
                self._questions.append(operation)
                # すぐに尋ねられるときは、ダイアログが読み上げられるので知らせない
                if self._main_window.can_ask():
                    return
        message = operation.get_finish_message()
        if message:
            self._messages.append(message)
        # ダイアログを開いている間などは一覧を更新できないので、先に知らせる
        if not self._main_window.can_update_in_background():
            self._flush_messages()
