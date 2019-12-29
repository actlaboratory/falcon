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

tasks=queue.Queue()

class _workerThreadBody(threading.Thread):
	def __init__(self,identifier):
		threading.Thread.__init__(self)
		self.cancellable=True
		self.log=getLogger("falcon.workerThread%d" % identifier)

	def run(self):
		while(True):
			item=tasks.get()
			self.log.debug("picked up job")
			if isinstance(item,str) and item=="stop":#ワーカースレッド終了
				self.log.debug("Received stop signal. Exiting thread...")
				tasks.task_done()
				break
			#end 終了
			func=item[0]
			params=item[1]
			func(params)
			tasks.task_done()
		#end while
	#end run

initialized=False

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
	"""全てのワーカースレッドを停止させる。"""
	log.debug("Stopping worker threads...")
	for i in range(len(threads)):
		tasks.put("stop")
	for elem in threads:
		elem.join()
	log.debug("Stopped")

def RegisterTask(func,param):
	"""関数とパラメータを指定して、ワーカースレッドに処理を任せる。"""
	log.debug("register")
	tasks.put((func,param))
