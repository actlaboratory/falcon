# -*- coding: utf-8 -*-
# Falcon Drive List tab
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
ドライブリストです。ファイルリストと比べると、機能が制限されます。
"""

import os
import wx

import browsableObjects
import errorCodes
import globalVars
import fileOperator
import fileSystemManager
import misc
import workerThreads
import workerThreadTasks

from simpleDialog import *
from . import base


class DriveListTab(base.FalconTabBase):
    """ドライブリストが表示されているタブ。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.networkListTask = None
        self._getNetworkList()

    def _getNetworkList(self):
        if self.networkListTask is not None:
            self.networkListTask.Cancel()
            self.networkListTask = None
        # end cancel previous
        self.networkListTask = workerThreads.RegisterTask(
            workerThreadTasks.GetNetworkResources,
            {
                "isReady": self.isReady,
                "onAppend": self.OnAppendNetworkResource,
                "onFinish": self.OnFinishNetworkResource})

    def isReady(self):
        return self.listObject is not None

    def OnAppendNetworkResource(self, resource):
        if self.listObject:
            self.listObject.AppendNetworkResource(resource)
            self._AppendElement(resource)
            return True
        else:
            return False

    def OnFinishNetworkResource(self, number):
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
        self.parent.SetShortcutEnabled(True)
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
            globalVars.app.hMainView.menu.RegisterMenuCommand(menu, (
                "TOOL_EJECT_DRIVE",
                "TOOL_EJECT_DEVICE",
            ))
        globalVars.app.hMainView.menu.RegisterMenuCommand(menu, (
            "VIEW_DRIVE_INFO",
            "FILE_SHOWPROPERTIES"
        ))
        globalVars.app.hMainView.PopupMenu(menu)

    def GetRootObject(self):
        """ドライブ詳細情報表示で用いる"""
        return self.GetFocusedElement()

    def OnClose(self):
        """ネットワークリソース一覧をキャンセルして大気"""
        if self.networkListTask:
            self.networkListTask.Cancel()

    def OnUpdate(self):
        """ネットワークリソース一覧の読み込み開始"""
        self._getNetworkList()
