# -*- coding: utf-8 -*-
# settings dialog

from enum import Enum, auto

import viewkit
import wx

from viewkit.creator import viewCreator

import constants
import globalVars


class ValueType(Enum):
    BOOL = auto()
    INT = auto()
    STRING = auto()
    DIC = auto()


READER_SELECTION = {
    "NOSPEECH": _("音声なし"),
    "AUTO": _("自動選択"),
    "SAPI5": "SAPI5",
    "CLIPBOARD": _("クリップボード出力"),
    "PCTK": "PC-Talker",
    "NVDA": "NVDA",
    "JAWS": "JAWS for Windows"
}
COLOR_MODE_SELECTION = {
    "white": _("標準"),
    "dark": _("ダーク")
}
LOG_LEVEL_SELECTION = {
    "50": "CRITICAL",
    "40": "ERROR",
    "30": "WARNING",
    "20": "INFO",
    "10": "DEBUG",
    "0": "ALL"
}
TEXT_WRAPPING_SELECTION = {
    "on": _("画面幅で折り返し"),
    "off": _("折り返さない")
}
LANGUAGE_SELECTION = constants.SUPPORTING_LANGUAGE


class SettingsWindow(viewkit.SubWindow):
    """環境設定を行うウィンドウ。OKボタンが押されると設定を保存する。"""

    def __init__(self, parent, ctx, title, parameters=None):
        super().__init__(parent, ctx, title, parameters)
        self.app = globalVars.app
        self._bindings = {}  # 作ったオブジェクトと設定項目の対応
        self._install_controls()
        self._load()
        self._on_proxy_setting_changed()  # 初期値を反映する為一度呼び出しておく

    def _page_creator(self, label, orient, **kwargs):
        """タブのページを作り、そこに部品を配置するためのViewCreatorを返す"""
        return viewkit.creator.ViewCreator(self.creator.getMode(), self.creator.getFont(), self.tab, None, orient, label=label, **kwargs)

    def _install_controls(self):
        """いろんなwidgetを設置する。"""
        creator = self.creator.makeChild(wx.VERTICAL, 20)
        self.tab = creator.tabCtrl(_("カテゴリ選択"))

        # general
        creator = self._page_creator(_("一般"), wx.VERTICAL, space=20, style=wx.ALL, margin=20)
        creator.staticText(_("起動時に開くフォルダ"))
        horizontal_creator = creator.makeChild(wx.HORIZONTAL, 0, "", wx.ALL | wx.EXPAND, margin=0)
        self.start_path, dummy = horizontal_creator.inputbox(_("起動時に開く場所"), proportion=1, text_layout=None)
        horizontal_creator.button(_("参照"), self._on_browse_dir)

        self.confirm_unrecyclable = creator.checkbox(_("ゴミ箱を使えない場所では、完全に削除するか確認する(&R)"))

        creator = creator.makeChild(viewCreator.GridBagSizer, 20, _("一般"), wx.ALL | wx.EXPAND, proportion=1)
        self.log_level, dummy = creator.combobox(_("ログ記録レベル(&L)"), list(LOG_LEVEL_SELECTION.values()))
        self.reader, dummy = creator.combobox(_("出力先(&O)"), list(READER_SELECTION.values()))
        self.fx_volume_spin, dummy = creator.spinCtrl(_("効果音の音量"), 0, 300, self._on_spin_changed)
        self.fx_volume_slider, dummy = creator.slider(_("効果音の音量"), 0, 300, self._on_slider_changed, enable_tab_focus=False)
        self.history_count, dummy = creator.spinCtrl(_("検索履歴の保持件数"), 0, 100)

        # preview
        creator = self._page_creator(_("プレビュー"), viewCreator.GridBagSizer, style=wx.ALL | wx.EXPAND, proportion=1, margin=20)
        self.header_line_count, dummy = creator.spinCtrl(_("テキストヘッダー行数"), 1, 100)
        self.footer_line_count, dummy = creator.spinCtrl(_("テキストフッター行数"), 1, 100)
        self.audio_volume_spin, dummy = creator.spinCtrl(_("プレビューの音量"), 0, 300, self._on_spin_changed)
        self.audio_volume_slider, dummy = creator.slider(_("プレビューの音量"), 0, 300, self._on_slider_changed, enable_tab_focus=False)

        # view
        creator = self._page_creator(_("表示/言語"), viewCreator.GridBagSizer, style=wx.ALL, margin=20)
        self.language, dummy = creator.combobox(_("言語(&L)"), list(LANGUAGE_SELECTION.values()))
        self.color_mode, dummy = creator.combobox(_("画面表示モード(&D)"), list(COLOR_MODE_SELECTION.values()))
        self.text_wrapping, dummy = creator.combobox(_("テキストの折り返し(&W)"), list(TEXT_WRAPPING_SELECTION.values()))

        # network
        creator = self._page_creator(_("ネットワーク"), wx.VERTICAL, space=20, style=wx.ALL, margin=20)
        self.update = creator.checkbox(_("起動時に更新を確認(&U)"))
        self.use_manual_setting = creator.checkbox(_("プロキシサーバーの情報を手動で設定する(&M)"), self._on_proxy_setting_changed)
        self.server, dummy = creator.inputbox(_("サーバーURL"))
        self.server.hideScrollBar(wx.HORIZONTAL)
        self.port, dummy = creator.spinCtrl(_("ポート番号"), 0, 65535, default_value=8080)
        # 既定では使わない（Web 用のプロキシは、FTP・SFTP のポートへの中継を断ることが多いため）
        self.remote_proxy = creator.checkbox(_("FTP・SFTP の接続にもプロキシを使う（HTTP の CONNECT で中継）(&F)"))

        # buttons
        footer = self.creator.makeChild(wx.HORIZONTAL, style=wx.ALIGN_RIGHT)
        footer.okbutton("OK", self._on_ok, proportion=1)
        footer.cancelbutton(_("キャンセル"), proportion=1)

    def _load(self):
        # general
        self._bind(self.start_path, "browse", "startpath", ValueType.STRING)
        self._bind(self.confirm_unrecyclable, "general", "confirm_unrecyclable", ValueType.BOOL)
        self._bind(self.reader, "speech", "reader", ValueType.DIC, READER_SELECTION)
        self._bind(self.log_level, "general", "log_level", ValueType.DIC, LOG_LEVEL_SELECTION)
        self._bind(self.fx_volume_spin, "speech", "fx_volume", ValueType.INT, 100, 0, 300)
        self.fx_volume_slider.SetValue(self.fx_volume_spin.GetValue())
        self._bind(self.history_count, "search", "history_count", ValueType.INT, 0, 0, 100)

        # preview
        self._bind(self.header_line_count, "preview", "header_line_count", ValueType.INT, 10, 1, 100)
        self._bind(self.footer_line_count, "preview", "footer_line_count", ValueType.INT, 10, 1, 100)
        self._bind(self.audio_volume_spin, "preview", "audio_volume", ValueType.INT, 100, 0, 300)
        self.audio_volume_slider.SetValue(self.audio_volume_spin.GetValue())

        # view
        self._bind(self.language, "general", "language", ValueType.DIC, LANGUAGE_SELECTION)
        # 表示モードはviewkitの設定として保存されている
        viewkit_settings = self.app_ctx.settings
        self.color_mode.SetValue(COLOR_MODE_SELECTION["dark" if viewkit_settings.getSetting("view.is_dark", False) else "white"])
        self.text_wrapping.SetValue(TEXT_WRAPPING_SELECTION["on" if viewkit_settings.getSetting("view.is_word_wrap", False) else "off"])

        # network
        self._bind(self.update, "general", "update", ValueType.BOOL)
        self._bind(self.use_manual_setting, "proxy", "usemanualsetting", ValueType.BOOL)
        self._bind(self.server, "proxy", "server", ValueType.STRING)
        self._bind(self.port, "proxy", "port", ValueType.STRING)
        self._bind(self.remote_proxy, "remote", "use_proxy", ValueType.BOOL, False)

    def _bind(self, obj, section, key, value_type, prm=None, prm2=None, prm3=None):
        """設定値を画面の部品に反映し、保存時のために対応を記録する"""
        settings = self.app.settings
        if value_type == ValueType.DIC:
            obj.SetValue(prm[settings.get_str(section, key, prm2 if prm2 is not None else list(prm.keys())[0], prm.keys())])
        elif value_type == ValueType.BOOL:
            obj.SetValue(settings.get_bool(section, key, True if prm is None else prm))
        elif value_type == ValueType.STRING:
            obj.SetValue(settings.get_str(section, key, "" if prm is None else prm, prm2))
        elif value_type == ValueType.INT:
            obj.SetValue(settings.get_int(section, key, prm, prm2, prm3))
        self._bindings[obj] = (value_type, section, key, prm)

    def _on_ok(self, event):
        self._save()
        event.Skip()

    def _save(self):
        settings = self.app.settings
        for obj, (value_type, section, key, prm) in self._bindings.items():
            if value_type == ValueType.DIC:
                settings.set(section, key, list(prm.keys())[obj.GetSelection()])
            else:
                settings.set(section, key, obj.GetValue())
        # 表示モードはviewkitの設定として保存する
        viewkit_settings = self.app_ctx.settings
        viewkit_settings.changeSetting("view.is_dark", list(COLOR_MODE_SELECTION.keys())[self.color_mode.GetSelection()] == "dark")
        viewkit_settings.changeSetting("view.is_word_wrap", list(TEXT_WRAPPING_SELECTION.keys())[self.text_wrapping.GetSelection()] == "on")
        self.app.save_settings()

    def _on_proxy_setting_changed(self, event=None):
        enabled = self.use_manual_setting.GetValue()
        self.server.Enable(enabled)
        self.port.Enable(enabled)

    def _on_browse_dir(self, event):
        d = wx.DirDialog(self, _("起動時に開くフォルダを選択"))
        if d.ShowModal() != wx.ID_CANCEL:
            self.start_path.SetValue(d.GetPath())
        d.Destroy()

    def _on_spin_changed(self, event):
        obj = event.GetEventObject()
        target = self.fx_volume_slider if obj == self.fx_volume_spin else self.audio_volume_slider
        target.SetValue(obj.GetValue())

    def _on_slider_changed(self, event):
        obj = event.GetEventObject()
        target = self.fx_volume_spin if obj == self.fx_volume_slider else self.audio_volume_spin
        target.SetValue(obj.GetValue())
