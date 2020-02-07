# -*- coding: utf-8 -*-
#Falcon listObject base
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import globalVars

from .constants import *
class FalconListBase(object):
	"""全てのリストに共通する基本クラス。"""
	def __init__(self):
		self.supportedSorts=[]
		self.sortCursor=0
		self.sortDescending=0

	#indexで指定した列が文字列searchに一致する行の行インデックスを返す
	def Search(self,search,index=0):
		"""文字列からインデックス番号に変換する。"""
		lst=self.GetItems()
		found=-1
		i=0
		for elem in lst:
			if elem[index]==search:
				return i
			#end 検索
			i+=1
		#end for
		#見つからない場合
		return -1

	def GetSortCursor(self):
		return self.sortCursor

	def SetSortCursor(self, val=-1):
		"""インデックスを指定すると、その位置へソートカーソルを移動。パラメータなしで、次のソートへ移動。実際にソートを適用するには、ApplySort を実行する。"""
		if val==self.sortCursor: return
		if len(self.supportedSorts)==0:
			globalVars.app.say(_("このリストはソートできません。"))
			return
		#ソート非対応
		self.sortCursor=self.sortCursor+1 if val==-1 else val
		if self.sortCursor==len(self.supportedSorts): self.sortCursor=0
		if self.sortCursor<0: self.sortCursor=0
		globalVars.app.say(GetSortDescription(self.supportedSorts[self.sortCursor]))

	def SetSortDescending(self,d):
		if d==self.sortDescending: return
		self.sortDescending=d
		s=_("昇順") if d==0 else _("降順")
		globalVars.app.say(s)

	def GetSortDescending(self):
		return self.sortDescending

	def ApplySort(self):
		"""ソートを適用。並び順と照準/降順は、setSortCursor / SetSortDescending で設定しておく。"""
		if len(self.supportedSorts)==0: return
		self._sort(self.supportedSorts[self.sortCursor],self.sortDescending)

	def GetSupportedSorts(self):
		"""サポートされているソートのタイプを取得する。"""
		return self.supportedSorts

	def _getSortFunction(self,attrib):
		if attrib==SORT_TYPE_BASENAME: return lambda x: x.basename
		if attrib==SORT_TYPE_FILESIZE: return lambda x: x.size
		if attrib==SORT_TYPE_MODDATE: return lambda x: x.modDate
		if attrib==SORT_TYPE_ATTRIBUTES: return lambda x: x.attributes
		if attrib==SORT_TYPE_TYPESTRING: return lambda x: x.typeString
		if attrib==SORT_TYPE_VOLUMELABEL: return lambda x: x.basename
		if attrib==SORT_TYPE_DRIVELETTER: return lambda x: x.letter
		if attrib==SORT_TYPE_FREESPACE: return lambda x: x.free
		if attrib==SORT_TYPE_TOTALSPACE: return lambda x: x.total
