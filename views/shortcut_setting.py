# -*- coding: utf-8 -*-
# Falcon shortcut setting view
# Note: All comments except these top lines will be written in Japanese.

import pythoncom
import viewkit
import wx

import shortcut_link
import views.keyConfig
from simpleDialog import dialog, errorDialog


def get_show_command_names():
    """実行時の大きさの値と表示名の組を、選択肢の順に返す"""
    return [
        (shortcut_link.SHOW_NORMAL, _("通常のウィンドウ")),
        (shortcut_link.SHOW_MINIMIZED, _("最小化")),
        (shortcut_link.SHOW_MAXIMIZED, _("最大化")),
    ]


def get_show_command_name(show_command: int):
    """実行時の大きさの表示名を返す"""
    return dict(get_show_command_names()).get(show_command, _("通常のウィンドウ"))


def get_hotkey_text(hotkey: int):
    """ショートカットキーの表示用の文字列を返す"""
    text = shortcut_link.hotkey_to_string(hotkey)
    return text if text != "" else _("なし")


def get_target_text(info: shortcut_link.ShortcutInfo):
    """リンク先の表示用の文字列を返す"""
    return info.target if info.has_path_target() else info.target_display_name


class ShortcutSettingParameters:
    """ShortcutSettingWindow に渡すパラメータ"""

    def __init__(self, path: str, info: shortcut_link.ShortcutInfo):
        # ショートカットファイルのパス
        self.path = path
        # 今の設定
        self.info = info


class ShortcutSettingWindow(viewkit.SubWindow):
    """
    ショートカットの設定を変更するウィンドウ。
    OK ボタンで検証と保存を行い、失敗したらウィンドウを閉じずにエラーを出す。結果は保存した設定（shortcut_link.ShortcutInfo）。
    """

    def __init__(self, parent, ctx, title, parameters: ShortcutSettingParameters):
        super().__init__(parent, ctx, title, parameters)
        info = parameters.info
        self.hotkey = info.hotkey
        self.saved_info = None

        creator = self.creator.makeChild(wx.VERTICAL, 10, style=wx.ALL, margin=20)
        target_style = wx.BORDER_RAISED if info.has_path_target() else wx.TE_READONLY
        self.target, dummy = creator.inputbox(_("リンク先"), self._on_target_changed, get_target_text(info), style=target_style, x=500)
        self.arguments, dummy = creator.inputbox(_("パラメータ"), default_value=info.arguments, x=500)
        self.working_directory, dummy = creator.inputbox(_("作業フォルダー"), default_value=info.working_directory, x=500)

        hotkey_creator = creator.makeChild(wx.HORIZONTAL, 10)
        self.hotkey_text, dummy = hotkey_creator.inputbox(_("ショートカットキー"), default_value=get_hotkey_text(self.hotkey), style=wx.TE_READONLY, x=300)
        hotkey_creator.button(_("設定"), self._on_set_hotkey)

        self.show_commands = get_show_command_names()
        show_command_names = [name for value, name in self.show_commands]
        show_command_values = [value for value, name in self.show_commands]
        self.show_command, dummy = creator.combobox(_("実行時の大きさ"), show_command_names, state=show_command_values.index(info.show_command))
        self.description, dummy = creator.inputbox(_("コメント"), default_value=info.description, x=500)
        self.run_as_admin = creator.checkbox(_("管理者として実行"), state=info.run_as_admin)
        self._update_run_as_admin()

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.okbutton(_("ＯＫ"), self._on_ok)
        footer.cancelbutton(_("キャンセル"))

    def result(self):
        return self.saved_info

    def _make_info(self):
        """入力内容から設定を作る"""
        info = shortcut_link.ShortcutInfo()
        if self.parameters.info.has_path_target():
            info.target = self.target.GetLineText(0).strip()
        info.target_display_name = self.parameters.info.target_display_name
        info.arguments = self.arguments.GetLineText(0)
        info.working_directory = self.working_directory.GetLineText(0).strip()
        info.hotkey = self.hotkey
        info.show_command = self.show_commands[self.show_command.GetSelection()][0]
        info.description = self.description.GetLineText(0)
        info.run_as_admin = self.run_as_admin.IsEnabled() and self.run_as_admin.GetValue()
        return info

    def _on_target_changed(self, event):
        self._update_run_as_admin()

    def _update_run_as_admin(self):
        """リンク先に応じて「管理者として実行」を有効・無効にする"""
        info = shortcut_link.ShortcutInfo()
        info.target = self.target.GetLineText(0).strip() if self.parameters.info.has_path_target() else ""
        self.run_as_admin.Enable(info.can_run_as_admin())

    def _on_set_hotkey(self, event):
        result = self.showSubWindow(views.keyConfig.KeyInputWindow, _("ショートカットキーの設定"), shortcut_link.HotkeyFilter())
        if result.code == wx.ID_OK and result.user_object is not None:
            self.hotkey = shortcut_link.string_to_hotkey(result.user_object)
            dialog(_("設定完了"), _("%s に設定しました。") % result.user_object, self)
        else:
            self.hotkey = 0
            dialog(_("設定完了"), _("解除しました。"), self)
        self.hotkey_text.SetValue(get_hotkey_text(self.hotkey))

    def _on_ok(self, event):
        info = self._make_info()
        if info.has_path_target() or self.parameters.info.has_path_target():
            # エクスプローラーと同じく、リンク先を変えたときは、存在する項目でなければ受け付けない
            if info.target == "":
                errorDialog(_("リンク先を入力してください。"), self)
                return
            if info.target != self.parameters.info.target and not shortcut_link.target_exists(info.target):
                errorDialog(_("リンク先 '%s' が見つかりません。パスとファイル名が正しいかどうか確認してください。") % info.target, self)
                return
        try:
            shortcut_link.save(self.parameters.path, info)
        except pythoncom.com_error as e:
            detail = e.args[1] if len(e.args) > 1 and e.args[1] else str(e)
            errorDialog(_("ショートカットの設定を保存できませんでした。") + "\n" + str(detail), self)
            return
        self.saved_info = info
        event.Skip()
