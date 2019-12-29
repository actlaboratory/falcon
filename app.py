# -*- coding: utf-8 -*-
#Falcon app GUI implementation
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
import accessible_output2.outputs.auto
import sys
import FalconConfigParser
import gettext
import logging
import os
import wx
from logging import getLogger, FileHandler, Formatter
from soundPlayer import pybass

import constants
import DefaultSettings
import errorCodes
import misc
import workerThreads
from views import main

class falconAppMain(wx.App):
	def initialize(self):
		"""アプリを初期化する。"""
		t=misc.Timer()
		self.frozen=hasattr(sys,"frozen")
		self.InitLogger()
		self.LoadSettings()
		self.InitTranslation()
		self.InitSound()
		self.InitCaches()
		workerThreads.Start()

		# 起動サウンドの再生
		self.PlaySound(self.config["sounds"]["startup"])

		# 音声読み上げの準備
		reader=self.config["speech"]["reader"]
		if(reader=="PCTK"):
			self.log.info("use reader 'PCTalker'")
			self.speech=accessible_output2.outputs.pc_talker.PCTalker()
		elif(reader=="NVDA"):
			self.log.info("use reader 'NVDA'")
			self.speech=accessible_output2.outputs.nvda.NVDA()
#		elif(reader=="SAPI4"):
#			self.log.info("use reader 'SAPI4'")
#			self.speech=accessible_output2.outputs.sapi4.Sapi4()
		elif(reader=="SAPI5"):
			self.log.info("use reader 'SAPI5'")
			self.speech=accessible_output2.outputs.sapi5.SAPI5()
		elif(reader=="AUTO"):
			self.log.info("use reader 'AUTO'")
			self.speech=accessible_output2.outputs.auto.Auto()
		else:
			self.config.set("speech","reader","AUTO")
			self.log.warning("Setting missed! speech.reader reset to 'AUTO'")
			self.speech=accessible_output2.outputs.auto.Auto()

		self.log.debug("finished environment setup (%f seconds from start)" % t.elapsed)

		# メインビューを表示
		self.hMainView=main.View()
		self.hMainView.Initialize()
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
		r="executable" if self.frozen else "interpreter"
		self.log.info("Starting Falcon as %s!" % r)

	def LoadSettings(self):
		"""設定ファイルを読み込む。なければデフォルト設定を適用し、設定ファイルを書く。"""
		self.config = DefaultSettings.DefaultSettings.get()
		self.config.read(constants.SETTING_FILE_NAME)

		self.config.write()

	def InitTranslation(self):
		"""翻訳を初期化する。"""
		self.translator=gettext.translation("messages","locale", languages=[self.config["general"]["language"]], fallback=True)
		self.translator.install()

	def InitSound(self):
		"""サウンド再生機能を初期化する。"""
		ret=pybass.BASS_Init(-1, 44100, 0, 0, 0)
		if ret!=1: self.log.error("BASS sound system could not be initialized.")

	def InitCaches(self):
		"""起動中に使用するキャッシュデータを初期化する。"""
		self.filetypes_cach={}#これほんとに使うかどうか検討中

	def GetFrozenStatus(self):
		"""コンパイル済みのexeで実行されている場合はTrue、インタプリタで実行されている場合はFalseを帰す。"""
		return self.frozen

	def say(self,s):
		"""スクリーンリーダーでしゃべらせる。"""
		self.speech.speak(s)

	def PlaySound(self,path):
		"""サウンドファイルを再生する。"""
		path="fx/"+path
		if not os.path.isfile(path):
			if path!="":
				self.log.error("Sound file '"+path+"' not found.")
			return
		handle=pybass.BASS_StreamCreateFile(False,path,0,0,pybass.BASS_STREAM_AUTOFREE|pybass.BASS_UNICODE)
		if handle==0:
			self.log.error("Cannot load sound file %s. Error code: %d" % (path, pybass.BASS_ErrorGetCode()))
			return
		#end error
		pybass.BASS_ChannelPlay(handle,True)
