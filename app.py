# -*- coding: utf-8 -*-
# Falcon app GUI implementation
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2022 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import datetime
import locale
import logging
import os
import sys
import threading
import traceback

import accessible_output2.outputs
import proxyUtil
import viewkit
import win32api
import wx

from accessible_output2.outputs.base import OutputError

import constants
import falcon_settings
import globalVars
import misc
import update
import UserCommandManager
import workerThreads

from falconSoundPlayer import pybass
from simpleDialog import dialog, winDialog


class FalconApp(viewkit.App):
    """viewkitのアプリケーションに、falcon固有の初期化処理を追加したもの"""

    def __init__(self, ctx: viewkit.ApplicationContext, initial_window, log_handler: logging.Handler):
        self.frozen = hasattr(sys, "frozen")
        self.log = logging.getLogger("%s.Main" % constants.LOG_PREFIX)
        self._log_handler = log_handler
        self.settings = falcon_settings.FalconSettings(ctx.settings)
        self.main_window = None
        self.error_sound_handle = None
        super().__init__(ctx, initial_window)

    def _initTranslation(self):
        """翻訳を初期化し、選択された言語を設定に保存する。"""
        super()._initTranslation()
        self.settings.set("general", "language", self.ctx.language)

    def _openMainWindow(self):
        """falcon固有の初期化を行ってから、メインウィンドウを開く"""
        self._initialize_falcon()
        t = misc.Timer()
        super()._openMainWindow()
        self.main_window = self.GetTopWindow()
        misc.InitContextMenu(self.main_window.GetHandle())
        self.log.debug("Finished mainView setup (%f seconds from start)" % t.elapsed)

    def _initialize_falcon(self):
        """falcon固有の初期化を行う。"""
        self._apply_log_level()
        self._set_locale()
        self._set_time_zone()
        self._init_speech()

        globalVars.update = update.update()
        # プロキシの設定を適用
        self.proxy_environ = proxyUtil.virtualProxyEnviron()
        self.set_proxy_environ()
        # スレッドで例外が起きてもsys.exceptHookが呼ばれるようにする
        self._install_thread_excepthook()
        # アップデートを実行
        if self.settings.get_bool("general", "update"):
            globalVars.update.update(True)

        t = misc.Timer()
        wx.DisableAsserts()
        self._init_sound()
        self.load_user_command_settings()
        self._load_user_extention_settings()
        workerThreads.Start()

        # 起動サウンドの再生
        self.play_sound(self.settings.get("sounds", "startup"))
        self.log.debug("finished environment setup (%f seconds from start)" % t.elapsed)

    def _apply_log_level(self):
        if self._log_handler is not None:
            self._log_handler.setLevel(self.settings.get_int("general", "log_level", 20, 0, 50))

    def _set_locale(self):
        try:
            value = self.settings.get("general", "locale")
            if value:
                locale.setlocale(locale.LC_TIME, value)
            else:
                locale.setlocale(locale.LC_TIME)
        except BaseException:
            locale.setlocale(locale.LC_TIME)
            self.settings.set("general", "locale", "")

    def _set_time_zone(self):
        bias = win32api.GetTimeZoneInformation(True)[1][0] * -1
        hours = bias // 60
        minutes = bias % 60
        self.timezone = datetime.timezone(datetime.timedelta(hours=hours, minutes=minutes))

    def _init_speech(self):
        """音声読み上げの準備"""
        try:
            self.speech = self._create_speech_output(self.settings.get("speech", "reader"))
        except OutputError:
            self.log.error("Failed to initialize speech output.")
            self.log.error(traceback.format_exc())
            winDialog(_("音声エンジンエラー"), _("音声読み上げ機能の初期化に失敗したため、読み上げ機能を使用できません。出力先の変更をお試しください。"))
            self.speech = accessible_output2.outputs.nospeech.NoSpeech()

    def _create_speech_output(self, reader):
        outputs = {
            "PCTK": accessible_output2.outputs.pc_talker.PCTalker,
            "NVDA": accessible_output2.outputs.nvda.NVDA,
            # SAPI4はバグってるっぽいので無効にしておく
            "SAPI5": accessible_output2.outputs.sapi5.SAPI5,
            "AUTO": accessible_output2.outputs.auto.Auto,
            "JAWS": accessible_output2.outputs.jaws.Jaws,
            "CLIPBOARD": accessible_output2.outputs.clipboard.Clipboard,
            "NOSPEECH": accessible_output2.outputs.nospeech.NoSpeech,
        }
        if reader not in outputs:
            self.settings.set("speech", "reader", "AUTO")
            self.log.warning("Setting missed! speech.reader reset to 'AUTO'")
            reader = "AUTO"
        self.log.info("use reader '%s'" % reader)
        return outputs[reader]()

    def _install_thread_excepthook(self):
        original_init = threading.Thread.__init__

        def init(thread, *args, **kwargs):
            original_init(thread, *args, **kwargs)
            original_run = thread.run

            def run(*args, **kwargs):
                try:
                    original_run(*args, **kwargs)
                except BaseException:
                    sys.excepthook(*sys.exc_info())
            thread.run = run

        threading.Thread.__init__ = init

    def load_user_command_settings(self):
        """お気に入りフォルダと「ここで開く」の設定を読み込む"""
        self.favorite_directory = UserCommandManager.UserCommandManager(
            self.settings.get_section("favorite_directories"),
            self.settings.get_section("favorite_directories_shortcut"),
            "MOVE_FAVORITE_FOLDER_")
        if self.favorite_directory.errors:
            message = _("お気に入りフォルダの設定が不正です。以下の設定を確認してください。\n\n")
            for v in self.favorite_directory.errors:
                message += v + "\n"
            dialog(_("エラー"), message)

        self.open_here_command = UserCommandManager.UserCommandManager(
            self.settings.get_section("open_here"),
            self.settings.get_section("open_here_shortcut"),
            "MOVE_OPEN_HERE_")
        if self.open_here_command.errors:
            message = _("「ここで開く」の設定が不正です。以下の設定を確認してください。\n\n")
            for v in self.open_here_command.errors:
                message += v + "\n"
            dialog(_("エラー"), message)

        self.user_command_managers = {
            self.favorite_directory: _("お気に入りディレクトリ"),
            self.open_here_command: _("ここで開く")
        }

    def _load_user_extention_settings(self):
        """サポートするドキュメント形式の追加設定を読み込む"""
        self.document_formats = set()
        document_formats = str(self.settings.get("extentions", "document")).split("/")
        err_audio = []
        err_format = []
        for ext in document_formats:
            ext = ext.lower()
            if ext in constants.SUPPORTED_AUDIO_FORMATS:
                err_audio.append(ext)
            if "." in ext:
                err_format.append(ext)
            else:
                self.document_formats.add(ext)
        if err_format:
            dialog(
                _("エラー"),
                _("以下の拡張子は、利用できない文字を含んでいるため登録できません。\n\n") +
                str(err_format))
        if err_audio:
            dialog(
                _("エラー"),
                _("以下の拡張子は、既に音声データの拡張子として登録されているため、テキスト形式として登録できません。\n\n") +
                str(err_audio))

    def _init_sound(self):
        """サウンド再生機能を初期化する。"""
        ret = pybass.BASS_Init(-1, 44100, 0, 0, 0)
        if ret != 1:
            self.log.error("BASS sound system could not be initialized.")

    def set_proxy_environ(self):
        if self.settings.get_bool("proxy", "usemanualsetting", False):
            self.proxy_environ.set_environ(self.settings.get("proxy", "server"), self.settings.get_int("proxy", "port", 8080, 0, 65535))
        else:
            self.proxy_environ.set_environ()

    def is_frozen(self):
        """コンパイル済みのexeで実行されている場合はTrue、インタプリタで実行されている場合はFalseを返す。"""
        return self.frozen

    def say(self, s, interrupt=False):
        """スクリーンリーダーでしゃべらせる。"""
        self.speech.speak(s, interrupt=interrupt)
        self.speech.braille(s)
        self.log.debug("speech: " + s + ", interrupt=" + str(interrupt))

    def play_sound(self, path, custom_location=False, volume=-1):
        """サウンドファイルを再生する。"""
        if not custom_location:
            path = "fx/" + path
        if not os.path.isfile(path):
            if path != "":
                self.log.error("Sound file '" + path + "' not found.")
            return -1
        handle = pybass.BASS_StreamCreateFile(
            False, path, 0, 0, pybass.BASS_STREAM_AUTOFREE | pybass.BASS_UNICODE)
        if handle == 0:
            self.log.error(
                "Cannot load sound file %s. Error code: %d" %
                (path, pybass.BASS_ErrorGetCode()))
            return -1
        if volume == -1:
            volume = self.settings.get_int("speech", "fx_volume", 100, 0, 300)
        pybass.BASS_ChannelSetAttribute(
            handle, pybass.BASS_ATTRIB_VOL, volume / 100)
        pybass.BASS_ChannelPlay(handle, True)
        return handle

    def stop_sound(self, handle):
        pybass.BASS_ChannelStop(handle)

    def play_error_sound(self):
        """例外が発生したときに音を鳴らす。"""
        if not self.error_sound_handle:
            self.error_sound_handle = pybass.BASS_StreamCreateFile(
                False,
                "fx\\internal_error.ogg",
                0,
                0,
                pybass.BASS_STREAM_AUTOFREE | pybass.BASS_UNICODE)
        pybass.BASS_ChannelPlay(self.error_sound_handle, True)

    def save_settings(self):
        """UserCommandManagerの内容を設定に反映し、設定ファイルに保存する"""
        if hasattr(self, "favorite_directory"):
            self.settings.replace_section("favorite_directories", self.favorite_directory.paramMap)
            self.settings.replace_section("favorite_directories_shortcut", self.favorite_directory.keyMap)
            self.settings.replace_section("open_here", self.open_here_command.paramMap)
            self.settings.replace_section("open_here_shortcut", self.open_here_command.keyMap)
        self.settings.save()

    def OnExit(self):
        workerThreads.Stop()
        self.save_settings()
        if globalVars.update:
            globalVars.update.runUpdate()
        return wx.App.OnExit(self)
