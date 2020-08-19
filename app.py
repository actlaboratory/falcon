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
import locale
import win32api
import datetime
import UserCommandManager
from logging import getLogger, FileHandler, Formatter
from soundPlayer import pybass
from simpleDialog import *

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
		self.error_sound_handle=None
		self.LoadSettings()
		wx.DisableAsserts()
		try:
			if self.config["general"]["locale"]!=None:
				locale.setlocale(locale.LC_TIME,self.config["general"]["locale"])
			else:
				locale.setlocale(locale.LC_TIME)
		except:
			locale.setlocale(locale.LC_TIME)
			self.config["general"]["locale"]=""
		self.SetTimeZone()
		self.InitTranslation()
		self.LoadUserCommandSettings()
		self.LoadUserExtentionSettings()
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
		elif(reader=="JAWS"):
			self.log.info("use reader 'JAWS'")
			self.speech=accessible_output2.outputs.jaws.Jaws()
		elif(reader=="CLIPBOARD"):
			self.log.info("use reader 'CLIPBOARD'")
			self.speech=accessible_output2.outputs.clipboard.Clipboard()
		elif(reader=="NOSPEECH"):
			self.log.info("use reader 'NOSPEECH'")
			self.speech=accessible_output2.outputs.nospeech.NoSpeech()
		else:
			self.config.set("speech","reader","AUTO")
			self.log.warning("Setting missed! speech.reader reset to 'AUTO'")
			self.speech=accessible_output2.outputs.auto.Auto()

		self.log.debug("finished environment setup (%f seconds from start)" % t.elapsed)

		# メインビューを表示
		self.hMainView=main.View()
		self.hMainView.Initialize()
		misc.InitContextMenu(self.hMainView.hFrame.GetHandle())
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
		if not self.config.read(constants.SETTING_FILE_NAME):
			#初回起動
			self.config.read_dict(DefaultSettings.initialValues)
			self.config.write()

	def LoadUserCommandSettings(self):
		"""お気に入りフォルダと「ここで開く」の設定を読み込む"""
		self.favoriteDirectory=UserCommandManager.UserCommandManager(self.config.items("favorite_directories"),self.config.items("favorite_directories_shortcut"),"MOVE_FAVORITE_FOLDER_")
		if self.favoriteDirectory.errors:
			tmp=_("お気に入りフォルダの設定が不正です。以下の設定を確認してください。\n\n")
			for v in self.favoriteDirectory.errors:
				tmp+=v+"\n"
			dialog(_("エラー"),tmp)

		self.openHereCommand=UserCommandManager.UserCommandManager(self.config.items("open_here"),self.config.items("open_here_shortcut"),"MOVE_OPEN_HERE_")
		if self.openHereCommand.errors:
			tmp=_("「ここで開く」の設定が不正です。以下の設定を確認してください。\n\n")
			for v in self.openHereCommand.errors:
				tmp+=v+"\n"
			dialog(_("エラー"),tmp)

		self.userCommandManagers={
				self.favoriteDirectory : _("お気に入りディレクトリ"),
				self.openHereCommand : _("ここで開く")
			}

	def LoadUserExtentionSettings(self):
		#サポートするドキュメント形式の追加設定
		self.documentFormats=set()
		documentFormats=self.config["extentions"]["document"].split("/")
		err_audio=[]
		err_format=[]
		for ext in documentFormats:
			ext=ext.lower()
			if ext in constants.SUPPORTED_AUDIO_FORMATS:
				err_audio.append(ext)
			if "." in ext:
				err_format.append(ext)
			else:
				self.documentFormats.add(ext)
		if err_format:
			dialog(_("エラー"),_("以下の拡張子は、利用できない文字を含んでいるため登録できません。\n\n")+str(err_format))
		if err_audio:
			dialog(_("エラー"),_("以下の拡張子は、既に音声データの拡張子として登録されているため、テキスト形式として登録できません。\n\n")+str(err_audio))

	def InitTranslation(self):
		"""翻訳を初期化する。"""
		self.translator=gettext.translation("messages","locale", languages=[self.config.getstring("general","language","ja-JP",constants.SUPPORTING_LANGUAGE)], fallback=True)
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

	def say(self,s,interrupt=False):
		"""スクリーンリーダーでしゃべらせる。"""
		self.speech.speak(s, interrupt=interrupt)
		self.speech.braille(s)

	def PlaySound(self,path,custom_location=False,volume=-1):
		"""サウンドファイルを再生する。"""
		if not custom_location: path="fx/"+path 
		if not os.path.isfile(path):
			if path!="":
				self.log.error("Sound file '"+path+"' not found.")
			return -1
		handle=pybass.BASS_StreamCreateFile(False,path,0,0,pybass.BASS_STREAM_AUTOFREE|pybass.BASS_UNICODE)
		if handle==0:
			self.log.error("Cannot load sound file %s. Error code: %d" % (path, pybass.BASS_ErrorGetCode()))
			return -1
		#end error
		if volume==-1:
			volume=self.config.getint("speech","fx_volume",100,0,300)
		pybass.BASS_ChannelSetAttribute(handle, pybass.BASS_ATTRIB_VOL, volume/100)
		pybass.BASS_ChannelPlay(handle,True)
		return handle

	def StopSound(self,handle):
		pybass.BASS_ChannelStop(handle)


	def OnExit(self):
		workerThreads.Stop()

		#UserCommandManagerの内容をconfigに反映し、この後の保存処理に備える
		del self.config["favorite_directories"]
		self.config["favorite_directories"]=self.favoriteDirectory.paramMap
		self.config["favorite_directories_shortcut"]=self.favoriteDirectory.keyMap
		del self.config["open_here"]
		self.config["open_here"]=self.openHereCommand.paramMap
		self.config["open_here_shortcut"]=self.openHereCommand.keyMap

		return wx.App.OnExit(self)

	def SetTimeZone(self):
		bias=win32api.GetTimeZoneInformation(True)[1][0]*-1
		hours=bias//60
		minutes=bias%60
		self.timezone=datetime.timezone(datetime.timedelta(hours=hours,minutes=minutes))

	def PlayErrorSound(self):
		"""例外が発生したときに音を鳴らす。"""
		if not self.error_sound_handle:
			self.error_sound_handle=pybass.BASS_StreamCreateFile(False,"fx\\internal_error.ogg",0,0,pybass.BASS_STREAM_AUTOFREE|pybass.BASS_UNICODE)
		#end load
		pybass.BASS_ChannelPlay(self.error_sound_handle,True)
