# -*- coding: utf-8 -*-
# settings dialog

import wx

import constants
import simpleDialog
import views.ViewCreator

from enum import Enum, auto
from views.baseDialog import *


class configType(Enum):
    BOOL = auto()
    INT = auto()
    STRING = auto()
    DIC = auto()


class Dialog(BaseDialog):
    readerSelection = {
        "NOSPEECH": _("音声なし"),
        "AUTO": _("自動選択"),
        "SAPI5": "SAPI5",
        "CLIPBOARD": _("クリップボード出力"),
        "PCTK": "PC-Talker",
        "NVDA": "NVDA",
        "JAWS": "JAWS for Windows"
    }
    colorModeSelection = {
        "white": _("標準"),
        "dark": _("ダーク")
    }
    logLevelSelection = {
        "50": "CRITICAL",
        "40": "ERROR",
        "30": "WARNING",
        "20": "INFO",
        "10": "DEBUG",
        "0": "NOTSET"
    }
    textWrappingSelection = {
        "on": _("画面幅で折り返し"),
        "off": _("折り返さない")
    }
    languageSelection = constants.SUPPORTING_LANGUAGE

    def __init__(self):
        super().__init__("settingsDialog")
        self.iniDic = {}  # iniファイルと作ったオブジェクトの対応

    def Initialize(self):
        self.log.debug("created")
        super().Initialize(self.app.hMainView.hFrame, _("設定"))
        self.InstallControls()
        self.load()
        self.checkBoxStatusChanged()  # 初期値を反映する為一度呼び出しておく
        return True

    def InstallControls(self):
        """いろんなwidgetを設置する。"""

        # tab
        self.creator = views.ViewCreator.ViewCreator(self.viewMode, self.panel, self.sizer, wx.VERTICAL, 20)
        self.tab = self.creator.tabCtrl(_("カテゴリ選択"))

        # general
        creator = views.ViewCreator.ViewCreator(self.viewMode, self.tab, None, views.ViewCreator.GridBagSizer,
                                                label=_("一般"), style=wx.ALL | wx.EXPAND, proportion=1, margin=20)
        self.startpath, static = creator.inputbox(_("起動時に開くフォルダ"))
        self.startpathBrowse = creator.button(_("参照"), self.browseDir,)
        self.logLevel, dummy = creator.combobox(_("ログ記録レベル(&L)"), list(self.logLevelSelection.values()))
        self.reader, static = creator.combobox(_("出力先(&O)"), list(self.readerSelection.values()))
        self.fxvolumeSpin, static = creator.spinCtrl(_("効果音の音量"), 0, 300, self.spinChanged)
        self.fxvolumeSlider, static = creator.slider(_("効果音の音量"), 0, 300, self.sliderChanged)
        self.historycount, static = creator.spinCtrl(_("検索履歴の保持件数"), 0, 100)

        # preview
        creator = views.ViewCreator.ViewCreator(self.viewMode, self.tab, None, views.ViewCreator.GridBagSizer,
                                                label=_("プレビュー"), style=wx.ALL | wx.EXPAND, proportion=1, margin=20)
        self.headerlinecount, static = creator.spinCtrl(_("テキストヘッダー行数"), 1, 100)
        self.footerlinecount, static = creator.spinCtrl(_("テキストフッター行数"), 1, 100)
        self.audiovolumeSpin, static = creator.spinCtrl(_("プレビューの音量"), 0, 300, self.spinChanged)
        self.audiovolumeSlider, static = creator.slider(_("プレビューの音量"), 0, 300, self.sliderChanged)

        # view
        creator = views.ViewCreator.ViewCreator(
            self.viewMode,
            self.tab,
            None,
            views.ViewCreator.GridBagSizer,
            label=_("表示/言語"),
            style=wx.ALL,
            margin=20)
        self.language, static = creator.combobox(_("言語(&L)"), list(self.languageSelection.values()))
        self.colormode, static = creator.combobox(_("画面表示モード(&D)"), list(self.colorModeSelection.values()))
        self.textwrapping, static = creator.combobox(_("テキストの折り返し(&W)"), list(self.textWrappingSelection.values()))

        # network
        creator = views.ViewCreator.ViewCreator(self.viewMode, self.tab, None, wx.VERTICAL, space=20, label=_("ネットワーク"), style=wx.ALL, margin=20)
        self.update = creator.checkbox(_("起動時に更新を確認(&U)"))
        self.usemanualsetting = creator.checkbox(_("プロキシサーバーの情報を手動で設定する(&M)"), self.checkBoxStatusChanged)
        self.server, static = creator.inputbox(_("サーバーURL"))
        self.server.hideScrollBar(wx.HORIZONTAL)
        self.port, static = creator.spinCtrl(_("ポート番号"), 0, 65535, defaultValue=8080)

        # buttons
        creator = views.ViewCreator.ViewCreator(self.viewMode, self.panel, self.sizer, wx.HORIZONTAL, style=wx.ALIGN_RIGHT)
        self.okbtn = creator.okbutton("OK", self.onOkButton, proportion=1)
        self.cancelBtn = creator.cancelbutton(_("キャンセル"), proportion=1)

    def load(self):
        # general
        self._setValue(self.startpath, "browse", "startpath", configType.STRING)
        self._setValue(self.reader, "speech", "reader", configType.DIC, self.readerSelection)
        self._setValue(self.logLevel, "general", "log_level", configType.DIC, self.logLevelSelection)
        self._setValue(self.fxvolumeSpin, "speech", "fx_volume", configType.INT, 100, 0, 300)
        self.fxvolumeSlider.SetValue(self.fxvolumeSpin.GetValue())
        self._setValue(self.historycount, "search", "history_count", configType.INT, 0, 0, 100)

        # preview
        self._setValue(self.headerlinecount, "preview", "header_line_count", configType.INT, 10, 1, 100)
        self._setValue(self.footerlinecount, "preview", "footer_line_count", configType.INT, 10, 1, 100)
        self._setValue(self.audiovolumeSpin, "preview", "audio_volume", configType.INT, 100, 0, 300)
        self.audiovolumeSlider.SetValue(self.audiovolumeSpin.GetValue())
        # view
        self._setValue(self.language, "general", "language", configType.DIC, self.languageSelection)
        self._setValue(self.colormode, "view", "colormode", configType.DIC, self.colorModeSelection)
        self._setValue(self.textwrapping, "view", "textwrapping", configType.DIC, self.textWrappingSelection)

        # network
        self._setValue(self.update, "general", "update", configType.BOOL)
        self._setValue(self.usemanualsetting, "proxy", "usemanualsetting", configType.BOOL)
        self._setValue(self.server, "proxy", "server", configType.STRING)
        self._setValue(self.port, "proxy", "port", configType.STRING)

    def onOkButton(self, event):
        result = self._save()
        event.Skip()

    def checkBoxStatusChanged(self, event=None):
        # proxy
        result = self.usemanualsetting.GetValue()
        self.server.Enable(result)
        self.port.Enable(result)

    def _setValue(self, obj, section, key, t, prm=None, prm2=None, prm3=None):
        assert isinstance(obj, wx.Window)
        assert type(section) == str
        assert type(key) == str
        assert type(t) == configType

        conf = self.app.config

        if t == configType.DIC:
            assert type(prm) == dict
            assert isinstance(obj, wx.ComboBox)
            obj.SetValue(prm[conf.getstring(section, key, prm2, prm.keys())])
        elif t == configType.BOOL:
            if prm is None:
                prm = True
            assert type(prm) == bool
            obj.SetValue(conf.getboolean(section, key, prm))
        elif t == configType.STRING:
            if prm is None:
                prm = ""
            assert type(prm) == str
            obj.SetValue(conf.getstring(section, key, prm, prm2))
        elif t == configType.INT:
            assert type(prm) == int
            assert type(prm2) == int
            assert type(prm3) == int
            obj.SetValue(conf.getint(section, key, prm, prm2, prm3))
        self.iniDic[obj] = (t, section, key, prm, prm2)

    def _save(self):
        conf = self.app.config
        for obj, v in self.iniDic.items():
            if v[0] == configType.DIC:
                conf[v[1]][v[2]] = list(v[3].keys())[obj.GetSelection()]
            else:
                conf[v[1]][v[2]] = obj.GetValue()
        conf.write()

    def browseDir(self, event):
        target = self.startpath
        dialog = wx.DirDialog(self.wnd, _("起動時に開くフォルダを選択"))
        result = dialog.ShowModal()
        if result == wx.ID_CANCEL:
            return
        target.SetValue(dialog.GetPath())

    def spinChanged(self, event):
        obj = event.GetEventObject()
        if obj == self.fxvolumeSpin:
            target = self.fxvolumeSlider
        elif obj == self.audiovolumeSpin:
            target = self.audiovolumeSlider
        target.SetValue(obj.GetValue())

    def sliderChanged(self, event):
        obj = event.GetEventObject()
        if obj == self.fxvolumeSlider:
            target = self.fxvolumeSpin
        elif obj == self.audiovolumeSlider:
            target = self.audiovolumeSpin
        target.SetValue(obj.GetValue())
