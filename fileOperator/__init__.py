# -*- coding: utf-8 -*-
#Falcon file operation handler main
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
import logging
import os
import pickle
import pywintypes
import random
import threading
import win32api
import win32event
from win32com.shell import shell, shellcon
from simpleDialog import dialog

import misc

from . import rename, failedElement

"""ファイルオペレーターのインスタンスを作って、辞書で支持を与えます。"""

class FileOperator(object):
	def __init__(self,instructions=None, elevated=False):
		"""指示を与える。まだ実行しない。"""
		self.elevated=elevated#昇格してるかどうか
		self.thread=None
		self.opTimer=None
		self.working=False#ファイルオペレーション実行中かどうか
		self.log=logging.getLogger("falcon.fileOperator")
		self.log.debug("Created.")
		self.output={}
		self.output["succeeded"]=0#オペレーション成功した数
		self.output["finished"]=False#オペレーション終了したかどうか
		self.output["failed"]=[]#失敗したファイル立ちの情報
		self.output["retry"]={"files": []}#権限昇格して自動的にリトライするオペレーション
		self.output["all_OK"]=False#全て成功ならTrueにする
		self.started=False#スタートしたかどうか
		self.instructions=None
		if isinstance(instructions,str):
			self.unpickle(instructions)
		else:
			self.instructions=instructions
		#end str or dict
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
			retry=rename.Execute(self.instructions,self.output)
		#end rename
		if retry: self._elevate()#昇格してリトライ
		self.working=False
		self.log.info("Finished (%f sec)" % self.opTimer.elapsed)
	#end _process

	def _elevate(self):
		"""権限昇格し、アクセス拒否になった項目を再実行する。"""
		dialog("elevating","elevating")
		o=FileOperator(self.output["retry"])
		fn=o.pickle()
		try:
			ret=shell.ShellExecuteEx(shellcon.SEE_MASK_NOCLOSEPROCESS,0,"runas","dist\\fileop.exe",fn)
		except pywintypes.error as e:
			self.log.error("Cannot elevate (%s)" % str(e))
			self.output["failed"].append(o.FailAll())
			dialog("error","error")
			return
		#end except
		pid=ret["hProcess"]
		win32event.WaitForSingleObject(pid,win32event.INFINITE)
		win32api.CloseHandle(pid)

	def FailAll(self):
		"""今ある要素を、全部失敗したことにする。権限昇格失敗したときに使う。"""
		lst=[]
		for elem in self.instructions["files"]:
			lst.append(failedElement.FailedElement(elem,"Access denied and elevation failed"))
		#end for
		return lst

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
			f=open(temp+"\\"+fi,"wb")
		except IOError:
			self.log.error("Failed to write to %s" % fi)
			return False
		#end except
		pickle.dump(self.instructions,f)
		f.close()
		try:
			f=open(temp+"\\"+fo,"wb")
		except IOError as er:
			self.debug.error("Failed to write to %s" % fo)
			return False
		#end except
		pickle.dump(self.output,f)
		f.close()
		return "falcon%04d" % r
	#end pickle

	def unpickle(self,name):
		"""ファイルから状態を読み込む。よみこめなかったらFalse。"""
		temp=win32api.GetEnvironmentVariable("TEMP")
		self.log.debug("Loading fileOp state from %s" % name)
		fi=name+"i"
		fo=name+"o"
		try:
			f=open(temp+"\\"+fi,"rb")
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
		f.close()
		try:
			f=open(temp+"\\"+fo,"rb")
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
		f.close()
		self.log.debug("Loaded (operation %s, infile %s" % (self.instructions["operation"], str(self.instructions["files"])))
		os.remove(temp+"\\"+fi)
		os.remove(temp+"\\"+fo)
		return True
