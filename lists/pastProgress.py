# -*- coding: utf-8 -*-
#Falcon past prrogress list object
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import os
import random
import re
import wx

import browsableObjects
import errorCodes
import misc

from .base import FalconListBase

class PastProgressList(FalconListBase):
	"""貼り付けの進捗状況を一覧するリスト。"""
	def __init__(self):
		super().__init__()
		#TODO: 並び順は、渓谷優先、エラー優先などあるといいですね
		self.supportedSorts=[]
		self.columns={
			_("項目名"):wx.LIST_FORMAT_LEFT,
			_("ステータス"): wx.LIST_FORMAT_RIGHT,
			_("詳細"): wx.LIST_FORMAT_LEFT,
		}
		self.results=[]
		self.headers=[]
		self.lists=[self.headers,self.results]

	def Initialize(self,another_instance=None):
		"""テストアイテムを作る"""
		if isinstance(another_instance,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			for elem in another_instance:
				self.results.append(elem)
			#end for
			return errorCodes.OK
		#end another_instance の処理
		head=browsableObjects.PastProgressHeader()
		head.Initialize("myfolder","path/to/myfolder","進行中","path/to/destination にコピーしています",50)
		self.headers.append(head)
		self.results.append(self._make(random.randint(0,9999),"用確認","宛先にすでにファイルが存在しています。"))
		self.results.append(self._make(random.randint(0,9999),"エラー","宛先ドライブに十分な空き領域がありません"))
		self.results.append(self._make(random.randint(0,9999),"エラー","アクセスが拒否されました。"))

	def _make(self,p1,p3,p4):
		o=browsableObjects.PastProgressItem()
		o.Initialize("test%04d" % (p1),"full\\path\\test%04d" % (p1),p3,p4)
		return o

	def Update(self):
		pass
