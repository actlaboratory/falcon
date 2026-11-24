# -*- coding: utf-8 -*-
# Falcon Drive List tab
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
ドライブリストです。ファイルリストと比べると、機能が制限されます。
"""

import os
import threading
import wx

import browsableObjects
import errorCodes
import globalVars
import fileOperator
import fileSystemManager
import lists.drive
import misc
import workerThreads
import workerThreadTasks

from simpleDialog import *
from . import base


def _run_task(task_state):
    """(別スレッド)ワーカースレッド用のタスクを、共用のワーカースレッドを使わずに実行する。"""
    task_state.setWorkingState(True)
    if task_state.func(task_state, task_state.params) is True:
        task_state.FinishCallback()
    else:
        task_state.CancelCallback()
    task_state.setWorkingState(False)


class DriveListTab(base.FalconTabBase):
    """ドライブリストが表示されているタブ。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.networkListTask = None
        self._closed = False
        # ドライブ一覧を作り直すたびに増やし、古い一覧に対する容量取得の結果を捨てるために使う
        self._drive_info_generation = 0
        self._getNetworkList()

    def _getNetworkList(self):
        if self.networkListTask is not None:
            self.networkListTask.Cancel()
            self.networkListTask = None
        # end cancel previous
        # ネットワーク上のコンピューターの列挙は数十秒かかることがあり、共用のワーカースレッドを占有しないように専用のスレッドで行う
        self.networkListTask = workerThreads.TaskState(
            workerThreadTasks.GetNetworkResources,
            {
                "isReady": self.isReady,
                "onAppend": self.OnAppendNetworkResource,
                "onFinish": self.OnFinishNetworkResource})
        threading.Thread(target=_run_task, args=(self.networkListTask,), daemon=True).start()

    def Update(self, lst, cursor=-1):
        super().Update(lst, cursor)
        self._start_loading_drive_info()

    def _start_loading_drive_info(self):
        """容量を取得していないネットワークドライブについて、ドライブごとに専用のスレッドで容量を取得する。"""
        self._drive_info_generation += 1
        for drive in self.listObject.GetPendingDrives():
            threading.Thread(
                target=self._load_drive_info,
                args=(drive, self._drive_info_generation),
                daemon=True).start()

    def _load_drive_info(self, drive, generation):
        """(別スレッド)ドライブの容量を取得し、メインスレッドに結果を渡す。"""
        loaded = lists.drive.GetDriveObject(ord(drive.letter) - 65)
        wx.CallAfter(self._on_drive_info_loaded, drive, loaded, generation)

    def _on_drive_info_loaded(self, drive, loaded, generation):
        """取得した容量を一覧に反映する。"""
        if self._closed or generation != self._drive_info_generation:
            return  # タブが閉じられたか、一覧が作り直された
        drive.free = loaded.free
        drive.total = loaded.total
        drive.info_pending = False
        if loaded.total < 0:
            drive.typeString = _("ネットワーク（未接続）")
        else:
            drive.hIcon = loaded.hIcon
        index = self.listObject.GetItemIndex(drive)
        if index < 0:
            return
        if drive.hIcon >= 0:
            icon_index = self.GetIconIndex(drive.hIcon)
            if icon_index >= 0:
                self.hListCtrl.SetItemImage(index, icon_index, icon_index)
        self.hListCtrl.RefreshItem(index)

    def isReady(self):
        return self.listObject is not None

    def OnAppendNetworkResource(self, resource):
        if self._closed:
            return False
        if self.listObject:
            self.listObject.AppendNetworkResource(resource)
            self._AppendElement(resource)
            return True
        else:
            return False

    def OnFinishNetworkResource(self, number):
        if self._closed:
            return
        if number == -1:
            dialog(_("エラー"), _("ネットワークリソース一覧が取得できませんでした。"))
        # end error
        self.log.debug("scanned network drives: %d" % number)
        self.networkTask = None

    def GoBackward(self):
        """内包しているフォルダ/ドライブ一覧へ移動する。"""
        return errorCodes.BOUNDARY

    def OnLabelEditEnd(self, evt):
        self.isRenaming = False
        self.parent.set_shortcut_enabled(True)
        if evt.IsEditCancelled():  # ユーザによる編集キャンセル
            return
        e = self.hListCtrl.GetEditControl()
        f = self.listObject.GetElement(self.GetFocusedItem())
        newName = e.GetLineText(0)
        error = fileSystemManager.ValidationObjectName(
            newName, fileSystemManager.pathTypes.VOLUME_LABEL, f.fullpath[0])
        if error:
            dialog(_("エラー"), error)
            evt.Veto()
            return
        inst = {"operation": "rename", "files": [
            f.fullpath[0:1]], "to": [newName]}
        op = fileOperator.FileOperator(inst)
        ret = op.Execute()
        if op.CheckSucceeded() == 0:
            dialog(_("エラー"), _("名前が変更できません。"))
            evt.Veto()
            return
        # end fail
    # end onLabelEditEnd

    def FileOperationTest(self):
        if self.task:
            self.task.Cancel()
        else:
            self.task = workerThreads.RegisterTask(workerThreadTasks.DebugBeep)

    def ReadCurrentFolder(self):
        globalVars.app.say(_("現在は、ドライブ洗濯"), interrupt=True)

    def ReadListItemNumber(self, short=False):
        if short:
            globalVars.app.say(
                _("ドライブ数 %(drives)d") % {
                    'drives': len(
                        self.listObject)})
        else:
            globalVars.app.say(_("ドライブ %(drives)d個") %
                               {'drives': len(self.listObject)}, interrupt=True)

    def ReadListInfo(self):
        globalVars.app.say(
            _("ドライブ一覧を %(sortkind)sの%(sortad)sで一覧中、 %(max)d個中 %(current)d個目") % {
                'sortkind': self.listObject.GetSortKindString(),
                'sortad': self.listObject.GetSortAdString(),
                'max': len(
                    self.listObject),
                'current': self.GetFocusedItem() + 1},
            interrupt=True)

    def GetTabName(self):
        """タブコントロールに表示する名前"""
        return _("ドライブ一覧")

    def OpenContextMenu(self, event):
        menu = wx.Menu()
        if isinstance(self.GetFocusedElement(), browsableObjects.Drive):
            globalVars.app.main_window.menu.register_menu_command(menu, (
                "TOOL_EJECT_DRIVE",
                "TOOL_EJECT_DEVICE",
            ))
        globalVars.app.main_window.menu.register_menu_command(menu, (
            "VIEW_DRIVE_INFO",
            "FILE_SHOWPROPERTIES"
        ))
        globalVars.app.main_window.PopupMenu(menu)

    def GetRootObject(self):
        """ドライブ詳細情報表示で用いる"""
        return self.GetFocusedElement()

    def OnClose(self):
        """ネットワークリソース一覧をキャンセルして大気"""
        # 閉じた後はリストコントロールが次のタブに引き継がれるため、遅れて届いた結果を反映しないようにする
        self._closed = True
        if self.networkListTask:
            self.networkListTask.Cancel()

    def OnUpdate(self):
        """ネットワークリソース一覧の読み込み開始"""
        self._getNetworkList()
