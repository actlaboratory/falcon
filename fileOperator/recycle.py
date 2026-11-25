# -*- coding: utf-8 -*-
# Falcon recycle bin helper
# Note: All comments except these top lines will be written in Japanese.

"""
項目をゴミ箱へ移動する処理です。ゴミ箱を使えない場所では、削除せずに失敗とします。

SHFileOperation は、ネットワーク上などゴミ箱のない場所では、確認なしに完全に削除してしまいます。
そこで IFileOperation を使い、削除の直前の通知で、ゴミ箱に入るかどうかを調べて止めます。
"""

import logging

import pythoncom
import pywintypes
import winerror
from win32com.server.exception import COMException
from win32com.server.policy import DesignatedWrapPolicy
from win32com.shell import shell, shellcon

log = logging.getLogger("falcon.recycle")

# IFileOperationProgressSink に渡される、ゴミ箱に入ることを示す印
_TSF_DELETE_RECYCLE_IF_POSSIBLE = 0x80
_FOFX_RECYCLEONDELETE = 0x00080000
_FLAGS = shellcon.FOF_ALLOWUNDO | shellcon.FOF_NOCONFIRMATION | shellcon.FOF_NO_UI | _FOFX_RECYCLEONDELETE

# アクセス拒否を表す HRESULT (E_ACCESSDENIED、COPYENGINE_E_REQUIRES_ELEVATION、COPYENGINE_E_ACCESS_DENIED_SRC)
_ACCESS_DENIED = (0x80070005, 0x80270002, 0x80270021)


class RecycleError(Exception):
    """ゴミ箱へ移動できなかった。code は HRESULT。"""

    def __init__(self, code):
        super().__init__("0x%08x" % code)
        self.code = code

    def is_access_denied(self):
        """アクセス拒否かどうかを返す"""
        return self.code in _ACCESS_DENIED


class NoRecycleBinError(RecycleError):
    """ゴミ箱を使えない場所なので、削除しなかった"""


class PermanentlyDeletedError(RecycleError):
    """事前の判定ではゴミ箱に入るはずだったが、完全に削除された"""


class Canceled(RecycleError):
    """利用者が中止した"""


class _ProgressSink(DesignatedWrapPolicy):
    """IFileOperation からの通知を受け取る。処理を止めるには、戻り値ではなく COMException を使う必要がある。"""

    _com_interfaces_ = [shell.IID_IFileOperationProgressSink]
    _public_methods_ = [
        "StartOperations", "FinishOperations", "PreRenameItem", "PostRenameItem", "PreMoveItem", "PostMoveItem",
        "PreCopyItem", "PostCopyItem", "PreDeleteItem", "PostDeleteItem", "PreNewItem", "PostNewItem",
        "UpdateProgress", "ResetTimer", "PauseTimer", "ResumeTimer"]

    def __init__(self, is_canceled):
        self._wrap_(self)
        self._is_canceled = is_canceled
        self.no_recycle_bin = False
        self.canceled = False
        # 最初に失敗した項目の HRESULT
        self.error_code = None
        self.permanently_deleted = False

    def _check_canceled(self):
        if self._is_canceled():
            self.canceled = True
            raise COMException(hresult=winerror.E_ABORT)

    def PreDeleteItem(self, flags, item):
        self._check_canceled()
        if not flags & _TSF_DELETE_RECYCLE_IF_POSSIBLE:
            self.no_recycle_bin = True
            raise COMException(hresult=winerror.E_ABORT)

    def PostDeleteItem(self, flags, item, result, new_item):
        if result < 0:
            if self.error_code is None:
                self.error_code = result & 0xffffffff
        elif new_item is None:
            self.permanently_deleted = True

    def UpdateProgress(self, total, done):
        self._check_canceled()

    def _ignore(self, *args):
        pass

    StartOperations = FinishOperations = PreRenameItem = PostRenameItem = PreMoveItem = PostMoveItem = _ignore
    PreCopyItem = PostCopyItem = PreNewItem = PostNewItem = ResetTimer = PauseTimer = ResumeTimer = _ignore


def move_to_recycle_bin(path, is_canceled):
    """項目をゴミ箱へ移動する。できなければ RecycleError。is_canceled は中止を指示されたかどうかを返す関数。"""
    sink = _ProgressSink(is_canceled)
    code = None
    try:
        item = shell.SHCreateItemFromParsingName(path, None, shell.IID_IShellItem)
        operation = pythoncom.CoCreateInstance(
            shell.CLSID_FileOperation, None, pythoncom.CLSCTX_ALL, shell.IID_IFileOperation)
        operation.SetOperationFlags(_FLAGS)
        operation.Advise(pythoncom.WrapObject(sink, shell.IID_IFileOperationProgressSink))
        operation.DeleteItem(item, None)
        operation.PerformOperations()
        if operation.GetAnyOperationsAborted():
            code = winerror.E_ABORT & 0xffffffff
    except pywintypes.com_error as e:
        code = e.hresult & 0xffffffff
    if sink.permanently_deleted:
        raise PermanentlyDeletedError(code or 0)
    if sink.canceled:
        raise Canceled(code or 0)
    if sink.no_recycle_bin:
        raise NoRecycleBinError(code or 0)
    if sink.error_code is not None or code is not None:
        raise RecycleError(sink.error_code if sink.error_code is not None else code)
