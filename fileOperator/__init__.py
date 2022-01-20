# -*- coding: utf-8 -*-
# Falcon file operation handler main
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.
import logging
import os
import pickle
import pywintypes
import random
import threading
import win32api
import win32event
import wx
from win32com.shell import shell, shellcon
from simpleDialog import dialog

import globalVars
import misc

from . import rename, changeAttribute, mkdir, trash, shortcut, symbolicLink, hardLink, delete, past
from . import failedElement, confirmElement

"""ファイルオペレーターのインスタンスを作って、辞書で支持を与えます。"""


class FileOperator(object):
    def __init__(self, instructions=None, elevated=False):
        """指示を与える。まだ実行しない。"""
        self.callbacks = {}
        self.elevated = elevated  # 昇格してるかどうか
        self.thread = None
        self.opTimer = None
        self.working = False  # ファイルオペレーション実行中かどうか
        self.log = logging.getLogger("falcon.fileOperator")
        self.log.debug("Created.")
        self.output = {}
        self.output["succeeded"] = 0  # オペレーション成功した数
        # 確認が必要な項目
        self.output["need_to_confirm"] = confirmElement.ConfirmationManager()
        self.output["finished"] = False  # オペレーション終了したかどうか
        self.output["failed"] = []  # 失敗したファイル立ちの情報
        self.output["retry"] = {"files": []}  # 権限昇格して自動的にリトライするオペレーション
        self.output["all_OK"] = False  # 全て成功ならTrueにする
        self.output["percentage"] = 0
        self.started = False  # スタートしたかどうか
        self.instructions = None
        # 確認に応答した後のファイル処理では、これが True
        # になっている。なので、エラーを無視したりとかする。処理に渡されたファイルは、問答無用で処理刷る(上書きするとかしないとかは、
        # confirmationManager が追加するかどうかのみに左右される)
        self.resume = False
        if isinstance(instructions, str):
            self.unpickle(instructions)
            self.writeBack = instructions
        else:
            self.instructions = instructions
        # end str or dict
    # end __init__

    def SetCallback(self, identifier, callable):
        """終了したときのコールバックを設定。"""
        self.callbacks[identifier] = callable

    def GetPercentage(self):
        return self.output["percentage"]

    def SetPercentage(self, p):
        self.output["percentage"] = p
        self._doCallback("setPercentage")

    def GetFinishedState(self):
        return self.output["finished"]

    def Execute(self, threaded=False):
        """
        ファイルオペレーションを実行。threaded=True にすると、バックグラウンドで実行される。
        この関数自体は、ファイルオペレーションが開始できたかどうかを帰すだけで、結果は通知しない。
        """
        print("op exec")
        if not self.instructions:
            self.log.error("No instructions specified.")
            return False
        # end 命令がない
        try:
            op = self.instructions["operation"]
        except KeyError:
            self.log.error(
                "operation is not specified in the given instructions.")
            return False
        # end キーがセットされてない
        op = op.lower()
        self.threaded = threaded
        self.started = True
        if threaded:
            self.thread = threading.Thread(target=self._process)
            self.thread.start()
        else:
            self._process()
        # end スレッドかそうじゃないか
        return True

    def _process(self):
        """ファイルオペレーション実行処理本体。スレッドで実行することもあるので、関数がべつになっている。"""
        self.working = True
        op = self.instructions["operation"]
        self.log.info("Starting file operation: %s" % op)
        self.opTimer = misc.Timer()
        if op == "rename":  # リネーム
            retry = rename.Execute(self)
        # end rename
        if op == "changeAttribute":  # 属性変更
            retry = changeAttribute.Execute(self)
        # end changeAttribute
        if op == "mkdir":  # フォルダ作成
            retry = mkdir.Execute(self)
        # end mkdir
        if op == "trash":  # ゴミ箱
            retry = trash.Execute(self)
        # end trash
        if op == "shortcut":
            retry = shortcut.Execute(self)
        # end shortcut
        if op == "symbolicLink":
            retry = symbolicLink.Execute(self)
        # end symbolicLink
        if op == "hardLink":
            retry = hardLink.Execute(self)
        # end hardLink
        if op == "delete":
            retry = delete.Execute(self)
        # end hardLink
        if op == "past":
            retry = past.Execute(self, resume=self.resume)
        # end hardLink
        self.log.debug(
            "success %s, retry %s, need to confirm %s, failure %s." %
            (self.output["succeeded"], retry, len(
                self.output["need_to_confirm"]), len(
                self.output["failed"])))
        if not self.elevated and retry > 0:
            self._elevate()  # 昇格してリトライ
        if self.elevated:
            self._postElevation()  # 昇格した後の後処理
        self.working = False
        self.log.info("Finished (%f sec)" % self.opTimer.elapsed)
        self._doCallback("finished")
    # end _process

    def _doCallback(self, identifier, parameters={}):
        if identifier not in self.callbacks:
            return
        if self.threaded:
            wx.CallAfter(self.callbacks[identifier], self, parameters)
        else:
            self.callbacks[identifier](self, parameters)
        # end スレッド実行の場合はcallAfter
# end _doCallback

    def _elevate(self):
        """権限昇格し、アクセス拒否になった項目を再実行する。"""
        if globalVars.app.GetFrozenStatus() is False:  # ビルド済みバイナリじゃないと昇格できないようにしてる
            dialog(_("エラー"), _("管理者権限の操作を行うためには、Falconをビルドして実行する必要があります。"))
            return
        # end ビルドしてないとダメ
        o = FileOperator(self.output["retry"])
        fn = o.pickle()
        try:
            ret = shell.ShellExecuteEx(
                shellcon.SEE_MASK_NOCLOSEPROCESS, 0, "runas", "fileop.exe", fn)
        except pywintypes.error as e:
            self.log.error("Cannot elevate (%s)" % str(e))
            self.output["failed"].append(o.FailAll())
            dialog("error", "error")
            return
        # end except
        pid = ret["hProcess"]
        win32event.WaitForSingleObject(pid, win32event.INFINITE)
        win32api.CloseHandle(pid)
        # 昇格先で失敗した項目を拾ってくる
        o = FileOperator(fn)
        self.output["succeeded"] += o.output["succeeded"]
        l = len(self.output["failed"])
        self.output["failed"][l:l] = o.output["failed"]
        self.log.debug("after elevation: success %s, failure %s." %
                       (self.output["succeeded"], len(self.output["failed"])))

    def _postElevation(self):
        """昇格して処理したので、状態を書き戻す。"""
        self.log.debug(
            "Processing post elevation, write back to %s." %
            self.writeBack)
        self.pickle(self.writeBack)

    def FailAll(self):
        """今ある要素を、全部失敗したことにする。権限昇格失敗したときに使う。"""
        lst = []
        for elem in self.instructions["files"]:
            lst.append(
                failedElement.FailedElement(
                    elem, "Access denied and elevation failed"))
        # end for
        return lst

    def CheckFinished(self):
        """ファイルオペレーションが終了したかどうかを取得する。"""
        print("started=%s working=%s" % (self.started, self.working))
        return self.started and not self.working
    # end CheckFinished

    def CheckAllOK(self):
        """終了したファイルオペレーションに対して、全ての処理が成功だったかどうかを取得する。"""
        return self.output["all_OK"]
    # end CheckAllOK

    def CheckSucceeded(self):
        """終了したファイルオペレーションに対して、いくつのファイルが処理成功したかを取得する。"""
        return self.output["succeeded"]
    # end CheckSucceeded

    def CheckFailed(self):
        """終了したファイルオペレーションに対して、処理失敗となった項目の情報を取得する。"""
        return self.output["failed"]

    def GetConfirmationCount(self):
        """確認待ちで停まっている項目の数を取得する。"""
        return len(self.output["need_to_confirm"])

    def GetConfirmationManager(self):
        """確認項目を取得するのに使える confirmationManager の参照を返す。"""
        return self.output["need_to_confirm"]

    def UpdateConfirmation(self):
        self.resume = True
        responded = list(self.output["need_to_confirm"].IterateResponded())
        for elem in responded:
            if elem.GetResponse() == "overwrite":
                self.instructions["target"].append((elem.elem.path, elem.elem.destpath))
                self.output["need_to_confirm"].Remove(elem)
            # end overwrite なら追加
        # end for
    # end UpdateConfirmation

    def pickle(self, name=""):
        """ファイルオペレーションの現在の状態を、テンポラリフォルダに保存する。保存したファイル名(完全なファイル名ではない)を帰す。これをそのまま unpickle に渡す。固められなかったらFalse。name に指定すると、強制的にその名前で書く。"""
        temp = win32api.GetEnvironmentVariable("TEMP")
        if name != "":
            fi = name + "i"
            fo = name + "o"
        else:
            while(True):
                r = random.randint(0, 9999)
                fi = "falcon%04di" % r
                fo = "falcon%04do" % r
                if os.path.isfile(fi) or os.path.isfile(fo):
                    continue
                break
            # end 保存できるファイル名を探す処理
        # end 強制指定かそうでないか
        self.log.debug(
            "Saving file operation status: directory=%s, filename=%s, %s" %
            (temp, fi, fo))
        try:
            f = open(temp + "\\" + fi, "wb")
        except IOError:
            self.log.error("Failed to write to %s" % fi)
            return False
        # end except
        pickle.dump(self.instructions, f)
        f.close()
        try:
            f = open(temp + "\\" + fo, "wb")
        except IOError as er:
            self.debug.error("Failed to write to %s" % fo)
            return False
        # end except
        pickle.dump(self.output, f)
        f.close()
        return "falcon%04d" % (r) if name == "" else name
    # end pickle

    def unpickle(self, name):
        """ファイルから状態を読み込む。よみこめなかったらFalse。"""
        temp = win32api.GetEnvironmentVariable("TEMP")
        self.log.debug("Loading fileOp state from %s" % name)
        fi = name + "i"
        fo = name + "o"
        try:
            f = open(temp + "\\" + fi, "rb")
        except IOError as er:
            self.log.error("Cannot read %s (%s)" % (fi, str(er)))
            return False
        # end except
        try:
            self.instructions = pickle.load(f)
        except (pickle.PickleError, EOFError) as err:
            self.log.error("Cannot extract %s(%s)" % (fi, str(err)))
            return False
        # end except
        f.close()
        try:
            f = open(temp + "\\" + fo, "rb")
        except IOError as er:
            self.log.error("Cannot read %s (%s)" % (fo, str(er)))
            return False
        # end except
        try:
            self.output = pickle.load(f)
        except (pickle.PickleError, EOFError) as err:
            self.log.error("Cannot extract %s(%s)" % (fo, str(err)))
            return False
        # end except
        f.close()
        os.remove(temp + "\\" + fi)
        os.remove(temp + "\\" + fo)
        return True
