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
import wx
import errorCodes
import listObjects
import browsableObjects
import globalVars
import constants

from simpleDialog import *
#アクションの識別子
ACTION_FORWARD=0#ファイル/フォルダ/副ストリームのオープン
ACTION_BACKWARD=1#内包しているフォルダ/内包しているドライブ/副ストリームのクローズ

class FalconTabBase(object):
	"""全てのタブに共通する基本クラス。"""
	def __init__(self):
		self.colums=[]#タブに表示されるカラムの一覧。外からは読み取りのみ。
		self.listObject=None#リストの中身を保持している listObjects のうちのどれかのオブジェクト・インスタンス
		self.type=None

	def __del__(self):
		pass

	def InstallListCtrl(self,parent):
		"""指定された親パネルの子供として、このタブ専用のリストコントロールを生成する。"""
		self.font = wx.Font(24,wx.FONTFAMILY_MODERN,wx.NORMAL,wx.FONTWEIGHT_BOLD)
		self.hListCtrl=wx.ListCtrl(parent, wx.ID_ANY, style=wx.LC_REPORT,size=wx.DefaultSize)
		self.hListCtrl.SetThemeEnabled(False)
		self.hListCtrl.SetBackgroundColour("#000000")		#項目のない部分の背景色
		#self.hListCtrl.SetForegroundColour("#ff0000")		#効果なし？
		self.hListCtrl.SetTextColour("#ffffff")				#文字色
		self.hListCtrl.SetFont(self.font)
		self.hListCtrl.Bind(wx.EVT_LIST_COL_END_DRAG,self.col_resize)
		self.hListCtrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED,self.EnterItem)

	def GetListColumns(self):
		return self.columns

	def GetItems(self):
		"""タブのリストの中身を取得する。"""
		return self.listObject.GetItems() if self.listObject is not None else []

	def GetFocusedItem(self):
		"""現在フォーカスが当たっているアイテムのインデックス番号を取得する。"""
		return self.hListCtrl.GetFocusedItem()

	def GetListCtrl(self):
		return self.hListCtrl

	def SetListColumns(self,col):
		"""リストコントロールにカラムを設定する。"""
		i=0
		for elem in col:
			self.hListCtrl.InsertColumn(i,elem,format=wx.LIST_FORMAT_LEFT,width=wx.LIST_AUTOSIZE)
			i+=1

	def UpdateListContent(self,content):
		"""リストコントロールの中身を更新する。カラム設定は含まない。"""
		self.hListCtrl.DeleteAllItems()
		for elem in content:
			self.hListCtrl.Append(elem)
		#end 追加
		self.log.debug("List control updated.")

	def TriggerAction(self, action):
		"""タブの指定要素に対してアクションを実行する。成功した場合は、errorCodes.OK を返し、失敗した場合は、その他のエラーコードを返す。"""
		return errorCodes.NOT_SUPPORTED#基底クラスではなにも許可しない

	def EnterItem(self):
		"""アイテムの上でエンターを押したときに実行される。本当はビューのショートカットキーにしたかったんだけど、エンターの入力だけはこっちでとらないとできなかった。"""
		return errorCodes.NOT_SUPPORTED#オーバーライドしてね

class MainListTab(FalconTabBase):
	"""ファイル/フォルダ/ドライブリストが表示されているタブ。"""
	def Initialize(self,parent):
		"""タブを初期化する。親ウィンドウの上にリストビューを作るだけ。"""
		self.log=logging.getLogger("falcon.mainListTab")
		self.log.debug("Created.")
		self.InstallListCtrl(parent)

	def Update(self,lst):
		"""指定された要素をタブに適用する。"""
		if type(self.listObject)!=lst:
			self.columns=lst.GetColumns()
			self.SetListColumns(self.columns)
		#end 違う種類のリストかどうか
		self.listObject=lst
		self.UpdateListContent(self.listObject.GetItems())

	def TriggerAction(self, action):
		index=self.GetFocusedItem()
		if action==ACTION_FORWARD:
			elem=self.listObject.GetElement(index)
			if isinstance(elem,browsableObjects.Folder):#このフォルダを開く
				lst=listObjects.FileList()
				ok=lst.Initialize(elem.fullpath)
				if not ok: return#アクセス負荷
				self.Update(lst)
				return errorCodes.OK
			#end フォルダ開く
			elif isinstance(elem,browsableObjects.Drive):#このドライブを開く
				lst=listObjects.FileList()
				lst.Initialize(elem.letter+":")
				self.Update(lst)
				return errorCodes.OK
			#end フォルダ開く

			else:
				return errorCodes.NOT_SUPPORTED#そのほかはまだサポートしてない
			#end フォルダ以外のタイプ
		#end ACTION_FORWARD
		if action==ACTION_BACKWARD:
			dir=self.listObject.rootDirectory
			if len(dir)<=3:#ドライブリスト
				lst=listObjects.DriveList()
				lst.Initialize()
				self.Update(lst)
				return
			#end ドライブ一覧表示
			predir=os.path.split(self.listObject.rootDirectory)[0]
			lst=listObjects.FileList()
			ok=lst.Initialize(predir)
			if not ok: return#アクセス負荷
			self.Update(lst)

	def col_resize(self,event):
		no=event.GetColumn()
		width=self.hListCtrl.GetColumnWidth(no)
		print("Column:"+str(no)+" resize to "+str(width))
		globalVars.app.config["MainView"]["column_width_"+str(no)]=str(width)
		with open(constants.SETTING_FILE_NAME, "w") as f: globalVars.app.config.write(f)

	def EnterItem(self,event):
		"""forward アクションを実行する。"""
		self.TriggerAction(ACTION_FORWARD)
