# -*- coding: utf-8 -*-
#Filer user commands manager
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import FalconConfigParser
import errorCodes
import menuItemsStore

class UserCommandManager:
	def __init__(self,params,keys,refHead):
		"""
			params,keymapは(name,value)のタプルのリスト
			configparser.items(section)の利用を想定
		"""

		#変数を初期化
		self.refHead=refHead
		self.keyMap={}
		self.paramMap={}
		self.refMap={}
		self.errors=[]

		self._addAll(params,keys)

	def add(self,name,param,key=None):
		"""指定した要素を追加する。すでに存在するなら上書きする。"""
		name=name.lower()
		self.paramMap[name]=param
		if key!=None:
			self.keyMap[name]=key
		else:
			#既に登録されている場合は削除
			if name in self.keyMap:
				del self.keyMap[name]
		self.refMap[menuItemsStore.getRef(self.refHead+name)]=name

	def _addAll(self,params,keys):
		"""引数の辞書からコマンドをまとめて登録する。nameが重複する場合は上書きする。keyが削除された時の対応などされていないので、各辞書が空の状態でのみ利用可能。"""
		dic={}

		#引数からconfigを生成
		dic["param"]=dict(params)
		dic["key"]=dict(keys)
		config=FalconConfigParser.FalconConfigParser()
		config.read_dict(dic)

		#configから２つのmapを生成
		for k in config.options("param"):
			if(config.has_option("key",k)):
				k=k.lower()
				self.paramMap[k]=config["param"][k]
				self.keyMap[k]=config["key"][k]
				self.refMap[menuItemsStore.getRef(self.refHead+k)]=k
			else:
				self.errors.append(k)

	def delete(self,name):
		"""指定されたnameの登録を削除する"""
		name=name.lower()
		del self.paramMap[name]
		if name in self.keyMap:
			del self.keyMap[name]
		del refMap[menuItemsStore.getRef(self.refHead+name)]

	def isRefHit(self,ref):
		"""指定したrefがこのインスタンスのものか否かを判定"""
		return ref in self.refMap

	def get(self,ref):
		"""指定されたrefに対応するparamを返す"""
		return self.paramMap[self.refMap[ref]]

	def replace(self,params,keys):
		"""全てのコマンドを削除し、引数で与えられたコマンドに置き換える。引数は__init__のものと同じ。"""
		self.keyMap={}
		self.paramMap={}
		self.refMap={}
		self.errors=[]
		self._addAll(params,keys)

	def __contains__(self, key):
		return key.lower() in self.paramMap

	def __len__(self):
		"""登録された要素の数を返す"""
		return len(self.paramMap)
