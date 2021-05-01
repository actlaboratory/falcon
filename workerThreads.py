# -*- coding: utf-8 -*-
# Falcon background thread manager
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.

"""
Falcon は、ワーカースレッドを提供します。ワーカースレッドに workerThreadTasks で定義しているタスクと引数を渡せば、バックグラウンドで実行してくれます。
"""

import logging
from logging import getLogger
import queue
import threading
import time
import misc

tasks = queue.Queue()

active_task_states = []


class Stop_task(object):
    pass


class TaskState(object):
    def __init__(self, func, params, cancelable=True):
        self.func = func
        self.params = params
        self.working = False
        self.canceled = False
        self.cancel_callback_done = False
        self.cancelable = cancelable
        self.finished = False

    def Cancel(self, wait=False):
        """タスクの実行を中断する。wait=Trueの場合、キャンセル処理がタスクに伝わり、実際に処理が終了するまでブロックする。"""
        if self.finished:
            return False  # すでに終わっている
        if not self.cancelable:
            return False
        self.canceled = True
        if self.working and wait:
            while(self.cancel_callback_done is False):
                time.sleep(0.05)
        return True

    def CancelCallback(self):
        """ワーカースレッドからのコールバック。キャンセル処理が正常に完了し、スレッドが終了したことを通知する。"""
        self.cancel_callback_done = True

    def FinishCallback(self):
        """タスクの終了を通知する。"""
        self.finished = True

    def GetFinishState(self):
        """タスクが完了していればTrue、完了していなければFalseを帰す。キャンセル済みタスクもFalseとなる。"""
        return self.finished

    def setWorkingState(self, w):
        """スレッドがタスクキューからこのタスクを拾って、実行を開始したときに呼び出すことで、状態が作業中になったことを知らせる。cancel(wait=True)メソッドで実行を待機する際、working=Trueかどうかで、実際に待つ処理をするかどうかを切り替えている。"""
        self.working = w


class _workerThreadBody(threading.Thread):
    def __init__(self, identifier):
        threading.Thread.__init__(self)
        self.log = getLogger("falcon.workerThread%d" % identifier)

    def run(self):
        while(True):
            item = tasks.get()
            self.log.debug("picked up job")
            if isinstance(item, Stop_task):  # ワーカースレッド終了
                self.log.debug("Received stop signal. Exiting thread...")
                tasks.task_done()
                break
            # end 終了
            if stopped:
                continue  # 終了した後にはタスクをもらっても働かない
            if item.canceled:  # 出したけどキャンセル済み
                tasks.task_done()
                self.log.debug("Already canceled, skipping this task...")
                continue
            # end キャンセル済みタスク
            func = item.func
            params = item.params
            active_task_states.append(item)
            t = misc.Timer()
            item.setWorkingState(True)
            ret = func(item, params)
            if ret is True:
                item.FinishCallback()
            else:
                item.CancelCallback()
            # end どっちのcallbackを呼ぶか
            tasks.task_done()
            self.log.debug(
                "task finished in %f seconds." %
                (t.elapsed) if ret else "Task canceled.")
            item.setWorkingState(False)
            active_task_states.remove(item)
        # end while
    # end run


initialized = False
stopped = False

threads = []


def Start(worker_num=2):
    """ワーカースレッドの数を指定して、初期化を行う。"""
    global initialized, log
    if initialized:
        return
    initialized = True
    log = getLogger("falcon.workerThreads")
    log.debug("%d worker threads initialized." % worker_num)
    for i in range(worker_num):
        t = _workerThreadBody(i + 1)
        t.start()
        threads.append(t)
    # end for
# end Initialize


def Stop():
    for elem in active_task_states:
        if not elem.cancelable:
            return False
    # end キャンセルできないタスクが走ってるかどうか

    stopped = True
    """全てのワーカースレッドを停止させる。"""
    log.debug("Stopping worker threads...")
    for elem in active_task_states:
        elem.Cancel()
    # end 実行中タスクキャンセル
    for i in range(len(threads)):
        tasks.put(Stop_task())
    for elem in threads:
        elem.join()
    log.debug("Stopped")


def RegisterTask(func, param={}):
    """関数とパラメータを指定して、ワーカースレッドに処理を任せる。タスクの状態を表すオブジェクトを返す。"""
    log.debug("register")
    t = TaskState(func, param)
    tasks.put(t)
    return t
