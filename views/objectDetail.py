# -*- coding: utf-8 -*-
# Falcon object detail view
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import logging

import pythoncom
import viewkit
import wx

import background_wait
import file_properties
import misc
import shortcut_link
import views.file_properties
import views.shortcut_setting
import workerThreads
import workerThreadTasks

from simpleDialog import errorDialog
from viewkit.creator import viewCreator

log = logging.getLogger("falcon.views.objectDetail")

# 計算中のフィールドを表す
CALCURATING = None


class ObjectDetailParameters:
    """
    ObjectDetailWindow に渡すパラメータ。
    items には (項目名, 内容, プロパティ) を表示順に追加する。内容に CALCURATING を指定した項目は、フォルダ容量の計算結果で埋められる。
    プロパティ（file_properties.PropertyItem）を指定し、それが変更できる項目なら、内容を直接書き換えられる（作成日時・更新日時）。
    """

    def __init__(self):
        self.items = []
        self.dir_calc_path = None  # 容量を計算するフォルダのパス
        self.shortcut_path = None  # ショートカットの設定を表示・変更するショートカットファイルのパス
        self.properties = None  # 表示・変更するプロパティ情報（file_properties.FileProperties）
        self.property_items = []  # プロパティの一覧に表示する項目

    def add(self, title, content, prop=None):
        self.items.append((title, content, prop))


class ObjectDetailWindow(viewkit.SubWindow):
    """ファイルやドライブなどの詳細情報を表示するウィンドウ"""

    def __init__(self, parent, ctx, title, parameters: ObjectDetailParameters):
        super().__init__(parent, ctx, title, parameters)
        self.task = None
        self.calcurating_fields = []
        # ファイルを変更したか（ショートカットの設定・プロパティ情報）
        self.modified = False
        self.shortcut_info = None
        self.shortcut_fields = []
        # 直接書き換えられる項目の (PropertyItem, 入力欄, 最初の内容)
        self.editable_fields = []
        self.property_list = None

        creator = self.creator.makeChild(viewCreator.FlexGridSizer, 20)
        for item_title, content, prop in parameters.items:
            if content is CALCURATING:
                field, dummy = creator.inputbox(item_title, x=400, default_value=_("計算中"), style=wx.TE_READONLY)
                self.calcurating_fields.append(field)
            elif prop is not None and prop.editable:
                field, dummy = creator.inputbox(item_title, x=400, default_value=str(content))
                self.editable_fields.append((prop, field, str(content)))
            else:
                creator.inputbox(item_title, x=400, default_value=str(content), style=wx.TE_READONLY)
        if parameters.shortcut_path is not None:
            self._add_shortcut_fields(creator, parameters.shortcut_path)
        if parameters.properties is not None:
            self._add_property_list(creator, parameters.properties, parameters.property_items)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        if self.shortcut_info is not None:
            footer.button(_("ショートカットの設定を変更(&L)..."), self._on_change_shortcut)
        if self.property_list is not None and self.property_list.has_editable_items():
            self.property_list.add_button(footer)
        if self.editable_fields or self.property_list is not None:
            footer.okbutton(_("ＯＫ"), self._on_ok)
            footer.cancelbutton(_("キャンセル"))
        else:
            footer.closebutton(_("ＯＫ"))

        if parameters.dir_calc_path is not None:
            param = {'lst': [(0, parameters.dir_calc_path)], 'callback': self._on_dir_calc_finished}
            self.task = workerThreads.RegisterTask(workerThreadTasks.DirCalc, param)

    def result(self):
        """ファイルを変更したか（ショートカットの設定・プロパティ情報）を返す"""
        return self.modified

    def _add_property_list(self, creator, properties, items):
        """プロパティ情報の一覧を追加する"""
        if not properties.writable and items:
            if properties.write_error:
                message = _("変更できません（%(reason)s）") % {"reason": properties.write_error}
            else:
                message = _("このファイルの種類では変更できません")
            creator.inputbox(_("プロパティの変更"), x=400, default_value=message, style=wx.TE_READONLY)
        if items:
            self.property_list = views.file_properties.PropertyList(self, creator, items)

    def _get_changes(self):
        """
        作成日時・更新日時の入力欄と、プロパティの一覧で変更した項目の (PropertyItem, 新しい値) のリストを返す。
        入力が正しくなければ、エラーを出して入力欄にフォーカスを移し、None を返す。
        """
        changes = []
        for prop, field, first_text in self.editable_fields:
            text = field.GetValue()
            if text.strip() == first_text.strip():
                continue
            try:
                changes.append((prop, file_properties.parse_input(prop, text)))
            except ValueError as e:
                errorDialog(str(e), self)
                field.SetFocus()
                return None
        if self.property_list is not None:
            changes += self.property_list.get_changes()
        return changes

    def _on_ok(self, event):
        """変更を書き込む。失敗したらウィンドウを閉じない"""
        changes = self._get_changes()
        if changes is None:
            return
        if changes:
            try:
                views.file_properties.save(self.parameters.properties.path, changes)
            except background_wait.Canceled:
                return
            except Exception as e:
                log.warning("cannot save the properties of %s (%s)" % (self.parameters.properties.path, e))
                views.file_properties.show_save_error(e, self)
                return
            self.modified = True
        event.Skip()

    def _get_shortcut_values(self):
        """ショートカットの設定の、表示する項目名と内容の一覧を返す"""
        info = self.shortcut_info
        return [
            (_("リンク先"), views.shortcut_setting.get_target_text(info)),
            (_("パラメータ"), info.arguments),
            (_("作業フォルダー"), info.working_directory),
            (_("ショートカットキー"), views.shortcut_setting.get_hotkey_text(info.hotkey)),
            (_("実行時の大きさ"), views.shortcut_setting.get_show_command_name(info.show_command)),
            (_("コメント"), info.description),
            (_("管理者として実行"), _("はい") if info.run_as_admin else _("いいえ")),
        ]

    def _add_shortcut_fields(self, creator, path):
        """ショートカットの設定の項目を追加する"""
        try:
            self.shortcut_info = shortcut_link.load(path)
        except pythoncom.com_error:
            creator.inputbox(_("リンク先"), x=400, default_value=_("ショートカットを読み込めませんでした。"), style=wx.TE_READONLY)
            return
        for item_title, content in self._get_shortcut_values():
            field, dummy = creator.inputbox(item_title, x=400, default_value=content, style=wx.TE_READONLY)
            self.shortcut_fields.append(field)

    def _on_change_shortcut(self, event):
        parameters = views.shortcut_setting.ShortcutSettingParameters(self.parameters.shortcut_path, self.shortcut_info)
        result = self.showSubWindow(views.shortcut_setting.ShortcutSettingWindow, _("ショートカットの設定"), parameters)
        if result.code == wx.ID_CANCEL or result.user_object is None:
            return
        self.shortcut_info = result.user_object
        self.modified = True
        for field, (item_title, content) in zip(self.shortcut_fields, self._get_shortcut_values()):
            field.SetValue(content)

    def Destroy(self):
        if self.task:
            self.task.Cancel()
            self.task = None
        return super().Destroy()

    def _on_dir_calc_finished(self, results, task_state):
        self.task = None
        result = results[0][1]  # 2つ以上来ることはなく、パス文字列は不要
        if result[0] >= 0:
            values = (
                misc.ConvertBytesTo(result[0], misc.UNIT_AUTO, True),
                str(result[0]),
                _("ファイル数： %(files)d サブディレクトリ数： %(dirs)d") % {"files": result[1], "dirs": result[2]},
            )
        else:
            values = (_("不明"), _("不明"), _("不明"))
        for field, value in zip(self.calcurating_fields, values):
            field.SetValue(value)
