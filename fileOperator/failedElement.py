# -*- coding: utf-8 -*-
#Falcon file operation handler failed elements
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
"""ファイルオペレーションに失敗したファイルの情報を表します。"""
class FailedElement(object):
	def __init__(self,elem,msg):
		self.elem=elem
		self.msg=msg
