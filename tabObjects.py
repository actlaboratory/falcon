# -*- coding: utf-8 -*-
#Falcon tab management
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
タブは、必ずリストビューです。カラムの数と名前と、それに対応するリストの要素がタブを構成します。たとえば、ファイル一覧では「ファイル名」や「サイズ」などがカラムになり、その情報がリストに格納されています。ファイル操作の状況を示すタブの場合は、「進行率」や「状態」などがカラムの名前として想定されています。リスト上でエンターを押すことで、アクションを実行できます。ファイルビューではファイルやフォルダを開き、ファイル操作では問い合わせに応答することができます。
"""

import os
import gettext
import logging
import errorCodes
import listObjects
import browsableObjects

#アクションの識別子
ACTION_FORWARD=0#ファイル/フォルダ/副ストリームのオープン
ACTION_BACKWARD=1#内包しているフォルダ/内包しているドライブ/副ストリームのクローズ

class FalconTabBase(object):
	"""全てのタブに共通する基本クラス。"""
	def __init__(self):
		self.colums=[]#タブに表示されるカラムの一覧。外からは読み取りのみ。
		self.listObject=None#リストの中身を保持している listObjects のうちのどれかのオブジェクト・インスタンス
	def __del__(self):
		pass

	def GetColumns(self):
		return self.columns

	def GetItems(self):
		"""タブのリストの中身を取得する。"""
		return self.listObject.GetItems() if self.listObject is not None else []

	def TriggerAction(self, index, action):
		"""タブの指定要素に対してアクションを実行する。成功した場合は、errorCodes.OK を返し、失敗した場合は、その他のエラーコードを返す。"""
		return errorCodes.NOT_SUPPORTED#基底クラスではなにも許可しない

class FileListTab(FalconTabBase):
	"""ファイルリストが表示されているタブ。"""
	def Initialize(self,dir):
		"""タブを初期化する。ディレクトリ名の指定で、ファイルリストを作成する。"""
		#カラム設定
		self.columns=[_("ファイル名"),_("サイズ"),_("更新"),_("属性"),_("種類")]
		self.log=logging.getLogger("falcon.fileListTab")
		self.log.debug("Created.")
		self.listObject=listObjects.FileList()
		self.listObject.Initialize(dir)

	def TriggerAction(self, index, action):
		if action==ACTION_FORWARD:
			elem=self.listObject.GetElement(index)
			if isinstance(elem,browsableObjects.Folder):#このフォルダを開く
				newList=listObjects.FileList()
				newList.Initialize(elem.fullpath)
				self.listObject=newList
				return errorCodes.OK
			#end フォルダ開く
			else:
				return errorCodes.NOT_SUPPORTED#そのほかはまだサポートしてない
			#end フォルダ以外のタイプ
		#end ACTION_FORWARD
		if action==ACTION_BACKWARD:
			preDir=os.path.split(self.listObject.rootDirectory)[0]
			if "\\" not in predir: return errorCodes.BOUNDARY#ファイルリストはこれ以上下がれないので、通知
			newList=listObjects.FileList()
			newList.Initialize(predir)
			self.listObject=newList

