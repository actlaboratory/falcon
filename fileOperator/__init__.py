# -*- coding: utf-8 -*-
#Falcon file operation handler main
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
import logging
import os
import pickle
import random
import threading
import win32api

import misc

from . import rename

"""ファイルオペレーターのインスタンスを作って、辞書で支持を与えます。"""

class FileOperator(object):
	def __init__(self,instructions=None):
		"""指示を与える。まだ実行しない。"""
		self.thread=None
		self.opTimer=None
		self.working=False#ファイルオペレーション実行中かどうか
		self.log=logging.getLogger("falcon.fileOperator")
		self.log.debug("Created.")
		self.instructions=instructions
		self.output={}
		self.output["succeeded"]=0#オペレーション成功した数
		self.output["finished"]=False#オペレーション終了したかどうか
		self.output["failed"]=[]#失敗したファイル立ちの情報
		self.output["all_OK"]=False#全て成功ならTrueにする
		self.started=False#スタートしたかどうか
	#end __init__

	def Execute(self, threaded=False):
		"""
		ファイルオペレーションを実行。threaded=True にすると、バックグラウンドで実行される。
		この関数自体は、ファイルオペレーションが開始できたかどうかを帰すだけで、結果は通知しない。
		"""
		if not self.instructions:
			self.log.error("No instructions specified.")
			return False
		#end 命令がない
		if self.started:
			self.log.error("This operation is already started.")
			return False
		#end すでに実行した
		try:
			op=self.instructions["operation"]
			files=self.instructions["files"]
		except KeyError:
			self.log.error("operation or file is not specified in the given instructions.")
			return False
		#end キーがセットされてない
		if len(files)==0:
			self.log.info("No files to process, skipping.")
			return False
		#end ファイルがない
		op=op.lower()
		if threaded:
			self.thread=threading.thread(self._process)
		else:
			self._process()
		#end スレッドかそうじゃないか
		return True

	def _process(self):
		"""ファイルオペレーション実行処理本体。スレッドで実行することもあるので、関数がべつになっている。"""
		self.working=True
		op=self.instructions["operation"]
		self.log.info("Starting file operation: %s" % op)
		self.opTimer=misc.Timer()
		if op=="rename":#リネーム
			rename.Execute(self.instructions,self.output)
		#end rename
		self.working=False
		self.log.info("Finished (%f sec)" % self.opTimer.elapsed)
	#end _process

	def CheckFinished(self):
		"""ファイルオペレーションが終了したかどうかを取得する。"""
		return self.started and not self.working
	#end CheckFinished

	def CheckAllOK(self):
		"""終了したファイルオペレーションに対して、全ての処理が成功だったかどうかを取得する。"""
		return self.output["all_OK"]
	#end CheckAllOK

	def CheckSucceeded(self):
		"""終了したファイルオペレーションに対して、いくつのファイルが処理成功したかを取得する。"""
		return self.output["succeeded"]
	#end CheckSucceeded

	def CheckFailed(self):
		"""終了したファイルオペレーションに対して、処理失敗となった項目の情報を取得する。"""
		return self.output["failed"]

	def pickle(self):
		"""ファイルオペレーションの現在の状態を、テンポラリフォルダに保存する。保存したファイル名(完全なファイル名ではない)を帰す。これをそのまま unpickle に渡す。固められなかったらFalse。"""
		temp=win32api.GetEnvironmentVariable("TEMP")
		while(True):
			r=random.randint(0,9999)
			fi="falcon%04di" % r
			fo="falcon%04do" % r
			if os.path.isfile(fi) or os.path.isfile(fo): continue
			break
		#end 保存できるファイル名を探す処理
		self.log.debug("Saving file operation status: directory=%s, filename=%s, %s" % (temp, fi, fo))
		try:
			f=open(fi,"wb")
		except IOError:
			self.log.error("Failed to write to %s" % fi)
			return False
		#end except
		pickle.dump(self.instructions,f)
		f.close()
		try:
			f=open(fo,"wb")
		except IOError as er:
			self.debug.error("Failed to write to %s" % fo)
			return False
		#end except
		pickle.dump(self.output,f)
		f.close()
		return "falcon%04" % r
	#end pickle

	def unpickle(self,name):
		"""ファイルから状態を読み込む。よみこめなかったらFalse。"""
		self.log.debug("Loading fileOp state from %s" % name)
		fi=name+"i"
		fo=name+"o"
		try:
			f=open(fi,"rb")
		except IOError as er:
			self.log.error("Cannot read %s (%s)" % (fi, str(er)))
			return False
		#end except
		try:
			self.instructions=pickle.load(f)
		except (pickle.PickleError, EOFError) as err:
			self.log.error("Cannot extract %s(%s)" % (fi, str(err)))
			return False
		#end except
		try:
			f=open(fo,"rb")
		except IOError as er:
			self.log.error("Cannot read %s (%s)" % (fo, str(er)))
			return False
		#end except
		try:
			self.output=pickle.load(f)
		except (pickle.PickleError, EOFError) as err:
			self.log.error("Cannot extract %s(%s)" % (fo, str(err)))
			return False
		#end except
		self.log.debug("Loaded")
		return True
