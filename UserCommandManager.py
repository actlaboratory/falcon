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
		dic={}

		#引数からconfigを生成
		dic["param"]=dict(params)
		dic["key"]=dict(keys)
		config=FalconConfigParser.FalconConfigParser()
		config.read_dict(dic)

		#configから２つのmapを生成
		for k in config.options("param"):
			if(config.has_option("key",k)):
				k=k.upper()
				self.paramMap[k]=config["param"][k]
				self.keyMap[k]=config["key"][k]
				self.refMap[menuItemsStore.getRef(refHead+k)]=k

			else:
				self.errors.append(k)

	def isRefHit(self,ref):
		"""指定したrefがこのインスタンスのものか否かを判定"""
		return ref in self.refMap

	def get(self,ref):
		"""指定されたrefに対応するparamを返す"""
		return self.paramMap[self.refMap[ref]]

	def add(self,name,param,key):
		"""指定した要素を追加"""
		name=name.upper()
		self.paramMap[name]=param
		self.keyMap[name]=key
		self.refMap[name]=menuItemsStore.getRef(self.refHead+name)

	def len(self):
		"""登録された要素の数を返す"""
		return len(self.paramMap)
