# -*- coding: utf-8 -*-
#Falcon app GUI implementation
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import configparser
import gettext
import logging
import wx
from logging import getLogger, FileHandler, Formatter

import constants
import DefaultSettings
import errorCodes

from views import main

class falconAppMain(wx.App):
	def initialize(self, ttl):
		"""タイトル"""
		t=misc.Timer()
		self.InitLogger()
		self.LoadSettings()
		self.InitTranslation()
		self.log.debug("finished environment setup (%f seconds from start)" % t.elapsed)
		#メインビューを表示
		self.hMainView=main.View()
		self.log.debug("Finished mainView setup (%f seconds from start)" % t.elapsed)
		return True

	def InitLogger(self):
		"""ロギング機能を初期化して準備する。"""
		self.hLogHandler=FileHandler("falcon.log", mode="w", encoding="UTF-8")
		self.hLogHandler.setLevel(logging.DEBUG)
		self.hLogFormatter=Formatter("%(name)s - %(levelname)s - %(message)s (%(asctime)s)")
		self.hLogHandler.setFormatter(self.hLogFormatter)
		self.log=getLogger("falcon")
		self.log.setLevel(logging.DEBUG)
		self.log.addHandler(self.hLogHandler)
		self.log.info("Starting Falcon.")

	def LoadSettings(self):
		"""設定ファイルを読み込む。なければデフォルト設定を適用し、設定ファイルを書く。"""
		self.config = DefaultSettings.DefaultSettings.get()
		if os.path.exists(constants.SETTING_FILE_NAME):
			self.config.read(constants.SETTING_FILE_NAME)
		with open(constants.SETTING_FILE_NAME, "w") as f: self.config.write(f)

	def InitTranslation(self):
		"""翻訳を初期化する。"""
		self.translator=gettext.translation("messages","locale", languages=[self.config["general"]["language"]], fallback=True)
		self.translator.install()
