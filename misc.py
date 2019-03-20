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

#ヘルパー関数群

UNIT_B=0
UNIT_KB=1
UNIT_MB=2
UNIT_GB=3
UNIT_TB=4
def ConvertBytesTo(b, unit):
	"""バイト数を受け取って、指定された単位を使ったサイズを返す。"""
	global UNIT_B, UNIT_KB, UNIT_MB, UNIT_GB
	if unit==UNIT_B: return b
	if unit==UNIT_KB: return b/1024
	if unit==UNIT_MB: return b/1024/1024
	if unit==UNIT_GB: return b/1024/1024/1024
	if unit==UNIT_TB: return b/1024/1024/1024/1024
	return 0

