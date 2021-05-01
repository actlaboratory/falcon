# -*- coding: utf-8 -*-
# Falcon app GUI implementation
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.

import os
import wx
import UserCommandManager
from soundPlayer import pybass
from simpleDialog import *

import AppBase
import constants
import misc
import workerThreads


class falconAppMain(AppBase.MaiｎBase):
    def __init__(self):
        super().__init__()

    def initialize(self):
        """アプリを初期化する。"""
        t = misc.Timer()

        wx.DisableAsserts()
        self.error_sound_handle = None
        self.InitSound()
        self.LoadUserCommandSettings()
        self.LoadUserExtentionSettings()
        self.InitCaches()
        workerThreads.Start()

        # 起動サウンドの再生
        self.PlaySound(self.config["sounds"]["startup"])

        self.log.debug(
            "finished environment setup (%f seconds from start)" %
            t.elapsed)

        # メインビューを表示
        from views import main
        self.hMainView = main.View("mainView")
        self.hMainView.Initialize()
        misc.InitContextMenu(self.hMainView.hFrame.GetHandle())
        self.log.debug(
            "Finished mainView setup (%f seconds from start)" %
            t.elapsed)
        return True

    def LoadUserCommandSettings(self):
        """お気に入りフォルダと「ここで開く」の設定を読み込む"""
        self.favoriteDirectory = UserCommandManager.UserCommandManager(
            self.config.items("favorite_directories"),
            self.config.items("favorite_directories_shortcut"),
            "MOVE_FAVORITE_FOLDER_")
        if self.favoriteDirectory.errors:
            tmp = _("お気に入りフォルダの設定が不正です。以下の設定を確認してください。\n\n")
            for v in self.favoriteDirectory.errors:
                tmp += v + "\n"
            dialog(_("エラー"), tmp)

        self.openHereCommand = UserCommandManager.UserCommandManager(self.config.items(
            "open_here"), self.config.items("open_here_shortcut"), "MOVE_OPEN_HERE_")
        if self.openHereCommand.errors:
            tmp = _("「ここで開く」の設定が不正です。以下の設定を確認してください。\n\n")
            for v in self.openHereCommand.errors:
                tmp += v + "\n"
            dialog(_("エラー"), tmp)

        self.userCommandManagers = {
            self.favoriteDirectory: _("お気に入りディレクトリ"),
            self.openHereCommand: _("ここで開く")
        }

    def LoadUserExtentionSettings(self):
        # サポートするドキュメント形式の追加設定
        self.documentFormats = set()
        documentFormats = self.config["extentions"]["document"].split("/")
        err_audio = []
        err_format = []
        for ext in documentFormats:
            ext = ext.lower()
            if ext in constants.SUPPORTED_AUDIO_FORMATS:
                err_audio.append(ext)
            if "." in ext:
                err_format.append(ext)
            else:
                self.documentFormats.add(ext)
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

    def InitSound(self):
        """サウンド再生機能を初期化する。"""
        ret = pybass.BASS_Init(-1, 44100, 0, 0, 0)
        if ret != 1:
            self.log.error("BASS sound system could not be initialized.")

    def InitCaches(self):
        """起動中に使用するキャッシュデータを初期化する。"""
        self.filetypes_cach = {}  # これほんとに使うかどうか検討中

    def PlaySound(self, path, custom_location=False, volume=-1):
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
        # end error
        if volume == -1:
            volume = self.config.getint("speech", "fx_volume", 100, 0, 300)
        pybass.BASS_ChannelSetAttribute(
            handle, pybass.BASS_ATTRIB_VOL, volume / 100)
        pybass.BASS_ChannelPlay(handle, True)
        return handle

    def StopSound(self, handle):
        pybass.BASS_ChannelStop(handle)

    def OnExit(self):
        workerThreads.Stop()

        # UserCommandManagerの内容をconfigに反映し、この後の保存処理に備える
        del self.config["favorite_directories"]
        self.config["favorite_directories"] = self.favoriteDirectory.paramMap
        self.config["favorite_directories_shortcut"] = self.favoriteDirectory.keyMap
        del self.config["open_here"]
        self.config["open_here"] = self.openHereCommand.paramMap
        self.config["open_here_shortcut"] = self.openHereCommand.keyMap

        return wx.App.OnExit(self)

    def PlayErrorSound(self):
        """例外が発生したときに音を鳴らす。"""
        if not self.error_sound_handle:
            self.error_sound_handle = pybass.BASS_StreamCreateFile(
                False,
                "fx\\internal_error.ogg",
                0,
                0,
                pybass.BASS_STREAM_AUTOFREE | pybass.BASS_UNICODE)
        # end load
        pybass.BASS_ChannelPlay(self.error_sound_handle, True)
