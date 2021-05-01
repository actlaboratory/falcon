# -*- coding: utf-8 -*-
#Falcon past prrogress list object
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import os
import re
import wx
from browsableObjects import PastProgressItem, PastProgressHeader

import errorCodes
import misc

import random

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

	def Initialize(self,another_instance=None, header_directory=""):
		"""テストアイテムを作る"""
		if isinstance(another_instance,list):#パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
			for elem in another_instance:
				self.results.append(elem)
			#end for
			return errorCodes.OK
		#end another_instance の処理
		head=PastProgressHeader()
		head.Initialize(header_directory,header_directory,"進行中","コピーしています",0)
		self.headers.append(head)

	def Update(self, confirmationManager=None):
		if not confirmationManager: return
		self.results.clear()
		for elem in confirmationManager.Iterate():
			path=elem.GetElement().path
			obj=PastProgressItem()
			obj.Initialize(os.path.basename(path),path,_("確認"),elem.GetMessageString())
			self.results.append(obj)
		#end 追加

	def SetHeaderPercentage(self,percentage):
		"""ヘッダーのパーセント表示を更新する。複数ヘッダーは想定してない。"""
		if len(self.headers)==0: return
		self.headers[0].SetPercentage(percentage)

	def GetHeaderObject(self):
		"""ヘッダーオブジェクトを取得。複数は想定してない。"""
		return self.headers[0] if len(self.headers)>0 else None

	def GetUnresolvedCount(self):
		"""未解決の項目の数を返す。"""
		return len(self.results)
