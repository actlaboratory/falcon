# -*- coding: utf-8 -*-
# Falcon file operation handler main
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.
import logging
import pywintypes
import threading
import win32wnet
import winerror
import wx
from simpleDialog import dialog

import globalVars
import misc

from . import rename, changeAttribute, mkdir, trash, shortcut, symbolicLink, hardLink, delete, past
from . import failedElement, confirmElement, elevation

"""ファイルオペレーターのインスタンスを作って、辞書で支持を与えます。"""

# 昇格したプロセスに渡すとき、割り当てたネットワークドライブのパスを UNC パスにする操作。
# ショートカットなどは、作るものの中身（リンク先）が変わってしまうので変換しない
_UNC_CONVERTIBLE_OPERATIONS = (past.VERB, delete.VERB, trash.VERB, mkdir.VERB)


def _get_owner_window():
    """UAC の画面の親にするウィンドウを返す。ない場合は 0。"""
    window = getattr(getattr(globalVars, "app", None), "main_window", None)
    try:
        return window.GetHandle() if window else 0
    except RuntimeError:  # ウィンドウが破棄されている
        return 0


def _to_unc(path):
    """割り当てたネットワークドライブ上のパスを UNC パスにする。それ以外はそのまま返す。"""
    if not isinstance(path, str) or len(path) < 2 or path[1] != ":":
        return path
    try:
        return win32wnet.WNetGetUniversalName(path, 1)  # 1: UNIVERSAL_NAME_INFO_LEVEL
    except pywintypes.error:  # ネットワークドライブではない
        return path


def _convert_targets_to_unc(instructions):
    """
    instructions["target"] のパスを UNC パスにした指示と、UNC パスから元のパスへの対応を返す。
    target の要素は、パスか、貼り付けの場合は (コピー元, コピー先) のタプル。
    """
    unc_map = {}
    if instructions.get("operation") not in _UNC_CONVERTIBLE_OPERATIONS:
        return instructions, unc_map

    def convert(path):
        unc = _to_unc(path)
        if unc != path:
            unc_map[unc] = path
        return unc

    targets = []
    for elem in instructions.get("target", []):
        if isinstance(elem, tuple):
            targets.append(tuple(convert(p) for p in elem))
        else:
            targets.append(convert(elem))
    converted = dict(instructions)
    converted["target"] = targets
    return converted, unc_map


def _restore_path(path, unc_map):
    """UNC パスにしたパスを、元のパスに戻す。フォルダの中の項目は、フォルダの部分だけを戻す。"""
    if not isinstance(path, str):
        return path
    for unc, original in unc_map.items():
        if path == unc or path.startswith(unc.rstrip("\\") + "\\"):
            return original + path[len(unc):]
    return path


def _restore_failed_paths(failed, unc_map):
    """失敗した項目のパスを、UNC パスから元のパスに戻す。"""
    for elem in failed:
        elem.elem = _restore_path(elem.elem, unc_map)
    return failed


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
        self._cancel = threading.Event()
        self.is_counting = False  # 処理する項目を数えている間は、割合がわからない
        self.instructions = instructions
    # end __init__

    def SetCallback(self, identifier, callable):
        """終了したときのコールバックを設定。"""
        self.callbacks[identifier] = callable

    def cancel(self):
        """中止を指示する。実際に止まるのは少し後。貼り付け、完全削除、ゴミ箱への移動が対応している。"""
        self._cancel.set()

    def is_canceled(self):
        """中止を指示されたかどうかを返す"""
        return self._cancel.is_set()

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
        """権限昇格し、アクセス拒否になった項目を再実行する。falcon 自身を、ファイル操作だけを行うモードで管理者権限で起動する。"""
        # 管理者権限のプロセスからは、割り当てたネットワークドライブが見えないので、UNC パスにして渡す
        instructions, unc_map = _convert_targets_to_unc(self.output["retry"])
        o = FileOperator(instructions)
        try:
            result = elevation.run_elevated(instructions, _get_owner_window())
        except elevation.ElevationCanceled:
            self.log.info("Elevation was canceled by the user.")
            self.output["failed"].extend(_restore_failed_paths(o.FailAll(), unc_map))  # FailAll はリストを返すので、要素として追加する
            return
        except elevation.ElevationError as e:
            self.log.error("Cannot elevate (%s)" % str(e))
            self.output["failed"].extend(_restore_failed_paths(o.FailAll(), unc_map))
            return
        # end except
        # 昇格先で失敗した項目を拾ってくる
        self.output["succeeded"] += result["succeeded"]
        self.output["failed"].extend(_restore_failed_paths(result["failed"], unc_map))
        for elem in result["confirmations"]:
            elem.elem.path = _restore_path(elem.elem.path, unc_map)
            elem.elem.destpath = _restore_path(elem.elem.destpath, unc_map)
            self.output["need_to_confirm"].Append(elem)
        self.log.debug("after elevation: success %s, failure %s." %
                       (self.output["succeeded"], len(self.output["failed"])))

    def _show_error(self, title, message):
        """エラーを表示する。別スレッドからはウィンドウを出せないので記録だけする(失敗した項目は CheckFailed でわかる)。"""
        if wx.IsMainThread():
            dialog(title, message)
        else:
            self.log.error(message)

    def FailAll(self):
        """今ある要素を、全部失敗したことにする。権限昇格失敗したときに使う。"""
        lst = []
        for elem in self.instructions["files"]:
            lst.append(
                failedElement.FailedElement(
                    elem, "Access denied and elevation failed"))
        # end for
        if self.instructions["operation"] == past.VERB:  # 貼り付けは (コピー元, コピー先) のタプルで持っている
            for elem in self.instructions["target"]:
                lst.append(failedElement.FailedElement(elem[0], (winerror.ERROR_ACCESS_DENIED, _("アクセスが拒否されました。"))))
        if self.instructions["operation"] in (delete.VERB, trash.VERB):
            for elem in self.instructions["target"]:
                lst.append(failedElement.FailedElement(elem, (winerror.ERROR_ACCESS_DENIED, _("アクセスが拒否されました。"))))
        return lst

    def CheckFinished(self):
        """ファイルオペレーションが終了したかどうかを取得する。"""
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
