﻿# -*- coding: utf-8 -*-
#Falcon miscellaneous helper objects
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import time

class Timer:
	"""シンプルなタイマー。経過時間や処理時間を計測するのに使う。単位は秒で、float。"""
	def __init__(self):
		self.started=time.time()

	@property
	def elapsed(self):
		return time.time()-self.started

#ヘルパー関数群

UNIT_AUTO=-1
UNIT_B=0
UNIT_KB=1
UNIT_MB=2
UNIT_GB=3
UNIT_TB=4
UNIT_STR=("B", "KB", "MB", "GB", "TB")

def ConvertBytesTo(b, unit, appendUnit=False):
	"""バイト数を受け取って、指定された単位を使ったサイズを返す。appendUnit=True にすると、単位の文字列を最後に付けてくれる。"""
	num=0
	if unit==UNIT_AUTO: unit=DetermineSizeUnit(b)
	if unit==UNIT_B:
		num=b
	elif unit==UNIT_KB:
		num=b/1024
	elif unit==UNIT_MB:
		num=b/1024/1024
	elif unit==UNIT_GB:
		num=b/1024/1024/1024
	if unit==UNIT_TB:
		num=b/1024/1024/1024/1024
	#end 単位
	ret="%.2f" % num
	if appendUnit: ret+=UNIT_STR[unit]
	return ret

def DetermineSizeUnit(b):
	"""バイト数を受け取って、それをサイズ単位に変換する際に最適な単位を、UNIT_* 定数で返す。"""
	global UNIT_B, UNIT_KB, UNIT_MB, UNIT_GB
	m=1024;
	if b<m: return UNIT_B
	m*=1024
	if b<m: return UNIT_KB
	m*=1024
	if b<m: return UNIT_MB
	m*=1024;
	if b<m: return UNIT_GB;
	return UNIT_TB;

def PTime2string(ptime):
	"""ptime 形式のオブジェクトを受け取って、人間が読めるタイムスタンプ文字列に変換して返す。"""
	return "%04d/%02d/%02d %02d:%02d:%02d" % (ptime.year, ptime.month, ptime.day, ptime.hour, ptime.minute, ptime.second)