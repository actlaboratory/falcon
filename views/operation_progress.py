# -*- coding: utf-8 -*-
# Falcon operation progress view
# Note: All comments except these top lines will be written in Japanese.

"""ファイル操作の進行状況と、確認・エラーの詳細を表示するウィンドウ"""

import datetime
import os
import time

import viewkit
import wx

import misc
import operation_manager
import views.extract
import views.OperationSelecter

from simpleDialog import dialog

# 進み具合を調べる間隔(ミリ秒)
_INTERVAL = 200
# 転送の状況の欄を書き換える間隔(秒)。読んでいる途中で変わりすぎないようにする
_STATUS_INTERVAL = 1


class OperationProgressWindow(viewkit.SubWindow):
    """ファイル操作の一覧。parameters は operation_manager.OperationManager。閉じても操作は続く。"""

    def __init__(self, parent, ctx, title, parameters: operation_manager.OperationManager):
        super().__init__(parent, ctx, title, parameters)
        self._operations = []
        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        self.list_ctrl, dummy = creator.listCtrl(_("ファイル操作"), self._on_focus, size=(700, 250))
        self.list_ctrl.InsertColumn(0, _("内容"), width=530)
        self.list_ctrl.InsertColumn(1, _("状態"), width=150)
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_detail)
        self.gauge, dummy = creator.gauge(_("実行中の操作"), x=400)
        self.gauge.SetRange(100)
        # 転送速度・残り時間など。Tab キーで移り、矢印キーで読めるように、読み取り専用の入力欄にする
        self.status, dummy = creator.inputbox(
            _("転送の状況"), style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_RAISED, x=500)
        self.status.SetMinSize((500, 90))
        self._status_time = 0

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        self.detail_button = footer.button(_("詳細") + "(&D)...", self._on_detail)
        self.cancel_button = footer.button(_("中止") + "(&S)", self._on_cancel)
        self.remove_button = footer.button(_("終了した操作を消去") + "(&R)", self._on_remove)
        footer.cancelbutton(_("閉じる"))

        self._load()
        self._update()
        self.list_ctrl.SetFocus()
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_timer, self._timer)
        self._timer.Start(_INTERVAL)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)

    def _on_destroy(self, event):
        if event.GetEventObject() is self:
            self._timer.Stop()
        event.Skip()

    def _load(self):
        """一覧を作り直し、確認待ち、実行中の順に探してカーソルを置く"""
        self.list_ctrl.DeleteAllItems()
        self._operations = list(self.parameters.operations)
        for operation in self._operations:
            self.list_ctrl.Append((operation.title, operation.get_state_string()))
        if not self._operations:
            return
        index = len(self._operations) - 1
        states = [operation.state for operation in self._operations]
        for state in (operation_manager.CONFIRMING, operation_manager.RUNNING):
            if state in states:
                index = states.index(state)
                break
        self.list_ctrl.Focus(index)
        self.list_ctrl.Select(index)

    def _get_focused(self):
        index = self.list_ctrl.GetFocusedItem()
        return self._operations[index] if 0 <= index < len(self._operations) else None

    def _update(self):
        """変わったところだけを表示に反映する。カーソルは動かさない。"""
        for i, operation in enumerate(self._operations):
            state = operation.get_state_string()
            if self.list_ctrl.GetItemText(i, 1) != state:
                self.list_ctrl.SetItem(i, 1, state)
        running = self.parameters.get_running()
        percentage = (running.get_percentage() or 0) if running is not None else 0
        if self.gauge.GetValue() != percentage:
            self.gauge.SetValue(percentage)
        self._update_status()
        self._update_buttons()

    def _update_status(self):
        """カーソルのある操作（実行中でなければ、実行中の操作）の、転送速度などを表示する"""
        operation = self._get_focused()
        if operation is None or operation.state != operation_manager.RUNNING:
            operation = self.parameters.get_running()
        lines = operation.get_status_lines() if operation is not None else []
        text = "\n".join(lines)
        current = self.status.GetValue()
        if current == text:
            return
        # 内容が変わり続けるときだけ間隔を空ける。表示し始めと、終わって消すときはすぐに反映する
        now = time.monotonic()
        if current and text and now - self._status_time < _STATUS_INTERVAL:
            return
        self._status_time = now
        # 読んでいる位置が先頭に戻らないようにする
        position = self.status.GetInsertionPoint()
        self.status.ChangeValue(text)
        self.status.SetInsertionPoint(min(position, self.status.GetLastPosition()))

    def _update_buttons(self):
        operation = self._get_focused()
        self._enable(self.detail_button, operation is not None and operation.has_detail())
        self._enable(self.cancel_button, operation is not None and operation.is_unfinished() and not operation.is_canceled())
        self._enable(self.remove_button, any(not operation.is_unfinished() for operation in self._operations))

    def _enable(self, button, enable):
        if button.IsEnabled() == enable:
            return
        if not enable and button.HasFocus():
            self.list_ctrl.SetFocus()  # フォーカスの行き先がなくならないようにする
        button.Enable(enable)

    def _on_timer(self, event):
        if not self.IsBeingDeleted():
            self._update()

    def _on_focus(self, event):
        self._update_buttons()
        # カーソルを動かしたら、その操作の状況をすぐに表示する
        self._status_time = 0
        self._update_status()
        event.Skip()

    def _on_detail(self, event):
        operation = self._get_focused()
        if operation is None or not operation.has_detail():
            return
        if operation.state == operation_manager.CONFIRMING and isinstance(operation, operation_manager.DeleteOperation):
            self.parameters.ask_permanent_delete(operation, self)
            self._update()
            self.list_ctrl.SetFocus()
            return
        if operation.state == operation_manager.CONFIRMING and isinstance(operation, operation_manager.ExtractOperation):
            result = self.showSubWindow(views.extract.PasswordWindow, _("パスワードの入力"), operation.get_password_message())
            if result.code == wx.ID_OK:
                operation.set_password(result.user_object)
        else:
            self.showSubWindow(OperationDetailWindow, _("ファイル操作の詳細"), operation)
        self.parameters.resume(operation)
        self._update()
        self.list_ctrl.SetFocus()

    def _on_cancel(self, event):
        operation = self._get_focused()
        if operation is not None:
            self.parameters.cancel(operation)
            self._update()

    def _on_remove(self, event):
        self.parameters.remove_finished()
        self._load()
        self._update()
        self.list_ctrl.SetFocus()


class OperationDetailWindow(viewkit.SubWindow):
    """確認が必要な項目と、エラーや注意の一覧。parameters は operation_manager.Operation。"""

    def __init__(self, parent, ctx, title, parameters: operation_manager.Operation):
        super().__init__(parent, ctx, title, parameters)
        creator = self.creator.makeChild(wx.VERTICAL, 20, style=wx.ALL | wx.EXPAND, margin=20)
        self.list_ctrl, dummy = creator.listCtrl(_("項目"), self._on_focus, size=(700, 300))
        self.list_ctrl.InsertColumn(0, _("項目名"), width=330)
        self.list_ctrl.InsertColumn(1, _("ステータス"), width=100)
        self.list_ctrl.InsertColumn(2, _("詳細"), width=250)
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_select)
        # 中止した操作の確認項目には応答できない
        self._confirmations = parameters.get_confirmations() if parameters.state == operation_manager.CONFIRMING else []
        for element in self._confirmations:
            self.list_ctrl.Append((element.GetElement().path, _("確認"), element.GetMessageString()))
        for target, kind, message in parameters.get_details():
            self.list_ctrl.Append((target, kind, message.replace("\n", " ")))
        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        self.select_button = footer.button(_("処理方法を選択") + "(&M)...", self._on_select)
        footer.cancelbutton(_("閉じる"))
        if self.list_ctrl.GetItemCount() > 0:
            self.list_ctrl.Focus(0)
            self.list_ctrl.Select(0)
        self._update_button()
        self.list_ctrl.SetFocus()

    def _get_focused(self):
        """カーソルのある確認項目を返す。確認項目でなければ None"""
        index = self.list_ctrl.GetFocusedItem()
        return self._confirmations[index] if 0 <= index < len(self._confirmations) else None

    def _update_button(self):
        self.select_button.Enable(self._get_focused() is not None)

    def _on_focus(self, event):
        self._update_button()
        event.Skip()

    def _on_select(self, event):
        confirmation = self._get_focused()
        if confirmation is None:
            return
        element = confirmation.GetElement()
        try:
            info = _get_information(element.path, element.destpath)
        except OSError as e:
            dialog(_("エラー"), e.strerror, self)
            return
        result = self.showSubWindow(
            views.OperationSelecter.OperationSelecterWindow, _("ファイル操作確認"),
            views.OperationSelecter.OperationSelecterParameters(
                _("上書きしますか？"), info, views.OperationSelecter.GetMethod("ALREADY_EXISTS"), True))
        self.list_ctrl.SetFocus()
        if result.code != wx.ID_OK:
            return
        response = result.user_object["response"]
        if result.user_object["all"]:
            self.parameters.operator.GetConfirmationManager().RespondAll(confirmation, response)
        else:
            confirmation.Respond(response)
        names = {value: name for name, value in views.OperationSelecter.GetMethod("ALREADY_EXISTS").items()}
        for i, item in enumerate(self._confirmations):
            # 閉じるまでは処理を始めないので、選び直すこともできる
            if item.IsResponded():
                self.list_ctrl.SetItem(i, 1, names[item.GetResponse()])


def _get_information(source, destination):
    """コピー元とコピー先を比べる情報を返す。どちらかを調べられない場合は OSError。"""
    # リンク先がないリンクの場合は、リンク自体の情報を使う
    source_stat = os.stat(source) if os.path.exists(source) else os.lstat(source)
    destination_stat = os.stat(destination) if os.path.exists(destination) else os.lstat(destination)
    return [
        (_("名前"), os.path.basename(source), "", ""),
        (_("サイズ"), misc.ConvertBytesTo(destination_stat.st_size, misc.UNIT_AUTO, True), "→",
         misc.ConvertBytesTo(source_stat.st_size, misc.UNIT_AUTO, True)),
        (_("更新日時"), datetime.datetime.fromtimestamp(destination_stat.st_mtime), "→",
         datetime.datetime.fromtimestamp(source_stat.st_mtime)),
    ]
