# -*- coding: utf-8 -*-
#Falcon background thread manager
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
Falcon は、ワーカースレッドを提供します。ワーカースレッドに関数と引数を渡せば、バックグラウンドで実行してくれます。
"""

import logging
from logging import getLogger
import queue
import threading
import misc

tasks=queue.Queue()

active_task_states=[]

class Stop_task(object):
	pass

class TaskState(object):
	def __init__(self,func,params,cancelable=True):
		self.func=func
		self.params=params
		self.canceled=False
		self.cancelable=cancelable
		self.finished=False

	def Cancel(self):
		if not self.cancelable: return False
		self.canceled=True
		return True

class _workerThreadBody(threading.Thread):
	def __init__(self,identifier):
		threading.Thread.__init__(self)
		self.log=getLogger("falcon.workerThread%d" % identifier)

	def run(self):
		while(True):
			item=tasks.get()
			self.log.debug("picked up job")
			if isinstance(item,Stop_task):#ワーカースレッド終了
				self.log.debug("Received stop signal. Exiting thread...")
				tasks.task_done()
				break
			#end 終了
			if stopped: continue#終了した後にはタスクをもらっても働かない
			if item.canceled:#出したけどキャンセル済み
				tasks.task_done()
				self.log.debug("Already canceled, skipping this task...")
				continue
			#end キャンセル済みタスク
			func=item.func
			params=item.params
			active_task_states.append(item)
			t=misc.Timer()
			ret=func(item,params)
			tasks.task_done()
			self.log.debug("task finished in %f seconds." % (t.elapsed) if ret else "Task canceled.")
			active_task_states.remove(item)
		#end while
	#end run

initialized=False
stopped=False

threads=[]

def Start(worker_num=2):
	"""ワーカースレッドの数を指定して、初期化を行う。"""
	global initialized, log
	if initialized: return
	initialized=True
	log=getLogger("falcon.workerThreads")
	log.debug("%d worker threads initialized." % worker_num)
	for  i in range(worker_num):
		t=_workerThreadBody(i+1)
		t.start()
		threads.append(t)
	#end for
#end Initialize

def Stop():
	for elem in active_task_states:
		if not elem.cancelable: return False
	#end キャンセルできないタスクが走ってるかどうか

	stopped=True
	"""全てのワーカースレッドを停止させる。"""
	log.debug("Stopping worker threads...")
	for elem in active_task_states:
		elem.Cancel()
	#end 実行中タスクキャンセル
	for i in range(len(threads)):
		tasks.put(Stop_task())
	for elem in threads:
		elem.join()
	log.debug("Stopped")

def RegisterTask(func,param={}):
	"""関数とパラメータを指定して、ワーカースレッドに処理を任せる。タスクの状態を表すオブジェクトを返す。"""
	log.debug("register")
	t=TaskState(func,param)
	tasks.put(t)
	return t