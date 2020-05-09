# -*- coding: utf-8 -*-
#Falcon listObject base
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import logging

import globalVars
import misc

from .constants import *

class FalconListBase(object):
	"""全てのリストに共通する基本クラス。"""
	def __init__(self):
		self.log=logging.getLogger("falcon."+self.__class__.__name__)
		self.supportedSorts=[]
		self.sortCursor=0
		self.sortDescending=0
		self.lists=[]		#内部のアイテムを保持するリストを表示順に格納
		self.columns={}

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
			globalVars.app.say(_("このリストはソートできません。"), interrupt=True)
			return
		#ソート非対応
		self.sortCursor=self.sortCursor+1 if val==-1 else val
		if self.sortCursor==len(self.supportedSorts): self.sortCursor=0
		if self.sortCursor<0: self.sortCursor=0
		globalVars.app.say(GetSortDescription(self.supportedSorts[self.sortCursor]), interrupt=True)

	def SetSortDescending(self,d):
		if d==self.sortDescending: return
		self.sortDescending=d
		s=_("昇順") if d==0 else _("降順")
		globalVars.app.say(s, interrupt=True)

	def GetSortDescending(self):
		return self.sortDescending

	def GetSortKindString(self):
		return GetSortDescription(self.supportedSorts[self.sortCursor])

	def GetSortAdString(self):
		return _("昇順") if self.sortDescending==0 else _("降順")

	def ApplySort(self):
		"""ソートを適用。並び順と照準/降順は、setSortCursor / SetSortDescending で設定しておく。"""
		if len(self.supportedSorts)==0: return
		self._sort(self.supportedSorts[self.sortCursor],self.sortDescending)

	def _sort(self,attrib, descending):
		"""指定した要素で、リストを並べ替える。"""
		self.log.debug("Begin sorting (attrib %s, descending %s)" % (attrib, descending))
		t=misc.Timer()
		f=self._getSortFunction(attrib)
		for l in self.lists:
			l.sort(key=f, reverse=(descending==1))
		self.log.debug("Finished sorting (%f seconds)" % t.elapsed)

	def GetSupportedSorts(self):
		"""サポートされているソートのタイプを取得する。"""
		return self.supportedSorts

	def GetElement(self,index):
		"""インデックスを指定して、対応するリスト内のオブジェクトを返す。"""
		for l in self.lists:
			if len(l)>index:
				return l[index]
			index-=len(l)
		return None

	def GetItems(self):
		"""リストの中身を文字列タプルで取得する。フォルダが上にくる。"""
		lst=[]
		for l in self.lists:
			for elem in l:
				lst.append(elem.GetListTuple())
		return lst

	def GetItemIndex(self,item):
		"""指定されたbrowsableObjectのインデックスを調べる"""
		beforeListCount=0	#前のリストのアイテム数
		for l in self.lists:
			if ret<0:
				try:
					ret=l.index(item)+beforeListCount
				except ValueError:
					ret=-1
				beforeListCount+=len(l)
		return ret

	def GetItemNames(self):
		"""リストの中身をファイル名のリストで取得する。"""
		lst=[]
		for l in self.lists:
			for i in l:
				lst.append(i.basename)
		return lst

	def GetItemList(self):
		"""browsableObjectのListを取得"""
		lst=[]
		for l in self.lists:
			lst+=l
		return lst

	def GetItemPaths(self):
		"""リストの中身をパスのリストで取得する。"""
		lst=[]
		for l in self.lists:
			for i in l:
				lst.append(i.fullpath)
		return lst

	def _getSortFunction(self,attrib):
		if attrib==SORT_TYPE_BASENAME: return lambda x: x.basename
		if attrib==SORT_TYPE_FILESIZE: return lambda x: x.size
		if attrib==SORT_TYPE_MODDATE: return lambda x: x.modDate
		if attrib==SORT_TYPE_ATTRIBUTES: return lambda x: x.attributesString
		if attrib==SORT_TYPE_TYPESTRING: return lambda x: x.typeString
		if attrib==SORT_TYPE_VOLUMELABEL: return lambda x: x.basename
		if attrib==SORT_TYPE_DRIVELETTER: return lambda x: x.letter
		if attrib==SORT_TYPE_FREESPACE: return lambda x: x.free
		if attrib==SORT_TYPE_TOTALSPACE: return lambda x: x.total
		if attrib==SORT_TYPE_HITCOUNT: return lambda x: x.hits
		if attrib==SORT_TYPE_HITLINE: return lambda x: x.ln
		if attrib==SORT_TYPE_PREVIEW: return lambda x: x.preview

	def GetColumns(self):
		"""このリストのカラム情報を返す。"""
		return self.columns

	def __iter__(self):
		return self.GetItemList().__iter__()

	def __len__(self):
		ret=0
		for l in self.lists:
			ret+=len(l)
		return ret
