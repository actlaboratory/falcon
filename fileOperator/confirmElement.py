# -*- coding: utf-8 -*-
#Falcon file operation handler confirm elements
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
"""ファイルオペレーションの結果、ユーザーに対して確認が必要になった項目を管理します。"""
class ConfirmElement(object):
	def __init__(self,elem,msg_number,msg_str):
		self.elem=elem
		self.msg_number=msg_number
		self.msg_str=msg_str
		self.response=None
		self.taken=False#ファイルオペレーションに回されたらTrue

	def GetElement(self):
		return self.elem

	def GetMessageNumber(self):
		return self.message_number

	def SetResponse(self,res):
		self.response=res

	def GetIfResponded(self):
		return self.response is not None

	def GetResponse(self):
		return self.response

	def __str__(self):
		return "[%s] %s (%s)" % (self.msg_number,self.msg_str,self.elem)

	def Take(self):
		self.taken=True

class ConfirmationManager(object):
	def __init__(self):
		self.confirmations=[]

	def Append(self,elem):
		self.confirmations.append(elem)

	def __len__(self):
		return len(self.confirmations)

	def Iterate(self):
		for elem in self.confirmations:
			if not elem.taken: yield elem

	def IterateNotResponded(self):
		for elem in self.confirmations:
			if not elem.taken and not elem.GetIfResponded(): yield elem

	def IterateWithFilter(self,number=None):
		for elem in self.confirmations:
			ok=True
			if elem.taken: ok=False
			if number is not None and elem.msg_number!=number: ok=False
			if ok:yield elem
		#end for
	#end IterateWithFilter

	def RespondAll(self,elem,response):
		"""指定したものより先にある、同じエラー番号の項目を、全て response として返答する。"""
		#インデックス番号を見つける
		i=0
		for e in self.confirmations:
			if e is elem: break
			i+=1
		#end インデックス番号を見つける
		msg_number=elem.GetMessageNumber()
		for i2 in range(i,len(self.confirmations)):
			if self.confirmations[i2].GetMessageNumber==message_number: self.confirmations[i].SetResponse(response)
		#end 全部応答
	#end RespondAll



	