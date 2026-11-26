# -*- coding: utf-8 -*-
# Falcon file properties view
# Note: All comments except these top lines will be written in Japanese.

"""詳細情報ウィンドウで、ファイルのプロパティ情報を表示・変更する部品"""

import viewkit
import wx

import background_wait
import file_properties
import globalVars

from simpleDialog import errorDialog

# 一覧の列
_COLUMN_LABEL = 0
_COLUMN_VALUE = 1
_COLUMN_STATE = 2
_COLUMN_GROUP = 3


def load(path):
    """
    プロパティ情報を別スレッドで読み込んで返す。メインスレッドから呼ぶ。
    利用者が中止したときは background_wait.Canceled、読み込めないときはその例外を投げる。
    """
    return background_wait.run(_load, path)


def _load(task, path):
    """(別スレッド)background_wait.run() で使う"""
    return file_properties.load(path)


def save(path, changes):
    """
    変更を別スレッドで書き込む。メインスレッドから呼ぶ。changes は (PropertyItem, 新しい値) のリスト。
    利用者が中止したときは background_wait.Canceled、書き込めないときはその例外を投げる。
    """
    background_wait.run(_save, path, changes)


def _save(task, path, changes):
    """(別スレッド)background_wait.run() で使う"""
    file_properties.save(path, changes)


class PropertyList:
    """
    プロパティ情報の一覧と「プロパティの変更」ボタン。
    変更した値は覚えておくだけで、書き込みは get_changes() を使って呼び出し側が行う。
    """

    def __init__(self, window: viewkit.SubWindow, creator, items):
        self._window = window
        # 一覧に表示する項目（file_properties.PropertyItem）
        self.items = items
        # 項目の名前 → 新しい値
        self._changes = {}
        self.edit_button = None

        self.list_ctrl, dummy = creator.listCtrl(
            _("プロパティ"), self._on_focus, size=(600, 250), style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list_ctrl.InsertColumn(_COLUMN_LABEL, _("項目"), width=160)
        self.list_ctrl.InsertColumn(_COLUMN_VALUE, _("値"), width=240)
        self.list_ctrl.InsertColumn(_COLUMN_STATE, _("変更"), width=100)
        self.list_ctrl.InsertColumn(_COLUMN_GROUP, _("分類"), width=100)
        for index, prop in enumerate(items):
            self.list_ctrl.InsertItem(index, prop.label)
            self.list_ctrl.SetItem(index, _COLUMN_GROUP, prop.group)
            self._update_row(index)
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_edit)
        if items:
            self.list_ctrl.Focus(0)
            self.list_ctrl.Select(0)

    def has_editable_items(self):
        """変更できる項目があるかを返す"""
        return any(prop.editable for prop in self.items)

    def add_button(self, footer):
        """「プロパティの変更」ボタンを置く"""
        self.edit_button = footer.button(_("プロパティの変更(&E)..."), self._on_edit)
        self._update_edit_button()

    def get_changes(self):
        """変更した項目の (PropertyItem, 新しい値) のリストを返す"""
        return [(prop, self._changes[prop.name]) for prop in self.items if prop.name in self._changes]

    def _selected_property(self):
        """選択中の項目を返す。なければ None"""
        index = self.list_ctrl.GetFocusedItem()
        if index < 0:
            return None
        return self.items[index]

    def _update_row(self, index):
        """一覧の1行の値と状態を表示し直す"""
        prop = self.items[index]
        if prop.name in self._changes:
            text = file_properties.format_value(prop, self._changes[prop.name])
            state = _("変更済み")
        else:
            text = prop.text
            state = _("変更できます") if prop.editable else ""
        self.list_ctrl.SetItem(index, _COLUMN_VALUE, text)
        self.list_ctrl.SetItem(index, _COLUMN_STATE, state)

    def _update_edit_button(self):
        if self.edit_button is None:
            return
        prop = self._selected_property()
        self.edit_button.Enable(prop is not None and prop.editable)

    def _on_focus(self, event):
        self._update_edit_button()

    def _on_edit(self, event):
        """選択中の項目を変更する"""
        prop = self._selected_property()
        if prop is None:
            return
        if not prop.editable:
            globalVars.app.say(_("この項目は変更できません。"), interrupt=True)
            return
        current = self._changes.get(prop.name, prop.value)
        result = self._window.showSubWindow(
            PropertyEditWindow, _("%(name)sの変更") % {"name": prop.label}, PropertyEditParameters(prop, current))
        if getattr(result, "code", wx.ID_CANCEL) == wx.ID_CANCEL:
            return
        value = result.user_object
        if file_properties.format_value(prop, value) == file_properties.format_value(prop, prop.value):
            self._changes.pop(prop.name, None)  # 元に戻した
        else:
            self._changes[prop.name] = value
        self._update_row(self.list_ctrl.GetFocusedItem())
        self.list_ctrl.SetFocus()


class PropertyEditParameters:
    """PropertyEditWindow に渡すパラメータ"""

    def __init__(self, prop: file_properties.PropertyItem, value):
        # 変更する項目
        self.prop = prop
        # 今の値（変更済みならその値）
        self.value = value


class PropertyEditWindow(viewkit.SubWindow):
    """
    プロパティの1項目の値を入力するウィンドウ。
    ＯＫ ボタンで入力を検証し、正しくなければウィンドウを閉じずにエラーを出す。結果は新しい値（値を消すときは None）。
    """

    def __init__(self, parent, ctx, title, parameters: PropertyEditParameters):
        super().__init__(parent, ctx, title, parameters)
        prop = parameters.prop
        self._value = parameters.value
        self.choice = None
        self.edit = None

        creator = self.creator.makeChild(wx.VERTICAL, 20, "", wx.EXPAND)
        if prop.kind == file_properties.KIND_CHOICE:
            labels = [label for dummy, label in prop.choices]
            values = [value for value, dummy in prop.choices]
            state = values.index(parameters.value) if parameters.value in values else 0
            self.choice, dummy = creator.combobox(prop.label, labels, state=state, x=400)
        else:
            text = file_properties.format_value(prop, parameters.value)
            self.edit, dummy = creator.inputbox(prop.label, default_value=text, x=400, style=wx.TE_DONTWRAP)
            creator.staticText(self._get_hint(prop), x=400)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, "", wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

    def _get_hint(self, prop):
        """入力欄の下に表示する説明を返す"""
        if prop.kind == file_properties.KIND_TEXT_LIST:
            return _("複数の値は「;」で区切って入力します。空にすると値を消します。")
        if prop.kind == file_properties.KIND_DATE:
            return _("「2024/01/31 13:45:00」の形で入力します。空にすると値を消します。")
        return _("空にすると値を消します。")

    def _on_ok(self, event):
        prop = self.parameters.prop
        if self.choice is not None:
            index = self.choice.GetSelection()
            self._value = prop.choices[index][0] if index >= 0 else None
            event.Skip()
            return
        try:
            self._value = file_properties.parse_input(prop, self.edit.GetValue())
        except ValueError as e:
            errorDialog(str(e), self)
            self.edit.SetFocus()
            return
        event.Skip()

    def result(self):
        return self._value


def show_save_error(error, parent):
    """書き込みに失敗したことを知らせる"""
    errorDialog(_("変更を保存できませんでした。\n%(error)s") % {"error": file_properties.get_error_message(error)}, parent)
