# -*- coding: utf-8 -*-
#Falcon miscellaneous helper objects
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import time

class Timer:
	"""シンプルなタイマー。経過時間や処理時間を計測するのに使う。単位はミリ秒。"""
	def __init__(self):
		self.started=time.time()

	@property
	def elapsed(self):
		return time.time()-self.started
