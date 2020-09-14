# -*- coding: utf-8 -*-
#Falcon tab base object
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
タブは、必ずリストビューです。カラムの数と名前と、それに対応するリストの要素がタブを構成します。たとえば、ファイル一覧では「ファイル名」や「サイズ」などがカラムになり、その情報がリストに格納されています。ファイル操作の状況を示すタブの場合は、「進行率」や「状態」などがカラムの名前として想定されています。リスト上でエンターを押すことで、アクションを実行できます。ファイルビューではファイルやフォルダを開き、ファイル操作では問い合わせに応答することができます。
"""
import copy
import json
import logging
import os
import pywintypes
import re

import wx
import browsableObjects
import clipboardHelper
import constants
import errorCodes
import fileOperator
import fileSystemManager
import globalVars
import history
import lists
import misc
import menuItemsStore

from win32com.shell import shell, shellcon

from . import navigator
from simpleDialog import *


#選択中のアイテム個数によるブロック
#ここに定義したものが__init__でコピーされる
#各インスタンスで追加は許されるが減らすことは許されない
selectItemMenuConditions=[]
selectItemMenuConditions.append([])
selectItemMenuConditions[0].extend([
	"FILE_RENAME",
	"FILE_CHANGEATTRIBUTE",
	"FILE_MAKESHORTCUT",
	"FILE_TRASH",
	"FILE_DELETE",
	"FILE_VIEW_DETAIL",
	"FILE_SHOWPROPERTIES",
	"EDIT_COPY",
	"EDIT_CUT",
	"EDIT_NAMECOPY",
	"EDIT_FULLPATHCOPY",
	"EDIT_OPENCONTEXTMENU",
	"EDIT_MARKITEM",
	"MOVE_FORWARD",
	"MOVE_FORWARD_ADMIN",
	"MOVE_FORWARD_TAB",
	"MOVE_FORWARD_STREAM",
	"MOVE_EXEC_ORIGINAL_ASSOCIATION",
	"TOOL_DIRCALC",
	"TOOL_HASHCALC",
	"TOOL_ADDPATH",
	"TOOL_EJECT_DRIVE",
	"TOOL_EJECT_DEVICE",
	"READ_CONTENT_PREVIEW",
	"READ_CONTENT_READHEADER",
	"READ_CONTENT_READFOOTER",
])
selectItemMenuConditions.append([])
selectItemMenuConditions.append([])
selectItemMenuConditions[2].extend([
	"FILE_RENAME",
	"FILE_MAKESHORTCUT",
	"FILE_VIEW_DETAIL",
	"FILE_SHOWPROPERTIES",
	"MOVE_FORWARD",
	"MOVE_FORWARD_ADMIN",
	"MOVE_FORWARD_TAB",
	"MOVE_FORWARD_STREAM",
	"MOVE_EXEC_ORIGINAL_ASSOCIATION",
	"TOOL_HASHCALC",
	"TOOL_EJECT_DRIVE",
	"TOOL_EJECT_DEVICE",
	"READ_CONTENT_PREVIEW",
	"READ_CONTENT_READHEADER",
	"READ_CONTENT_READFOOTER",
])

class FalconTabBase(object):
	"""全てのタブに共通する基本クラス。"""

	selectItemTypeMenuConditions={}
	selectItemTypeMenuConditions[browsableObjects.File]=[]
	selectItemTypeMenuConditions[browsableObjects.File].extend([
		"TOOL_DIRCALC",
		"MOVE_FORWARD_TAB",
		"TOOL_ADDPATH",
		"MOVE_FORWARD_TAB",
		"TOOL_EJECT_DRIVE",
		"TOOL_EJECT_DEVICE"
	])

	selectItemTypeMenuConditions[browsableObjects.Folder]=[]
	selectItemTypeMenuConditions[browsableObjects.Folder].extend([
		"TOOL_HASHCALC",
		"READ_CONTENT_PREVIEW",
		"READ_CONTENT_READHEADER",
		"READ_CONTENT_READFOOTER",
		"TOOL_EJECT_DRIVE",
		"TOOL_EJECT_DEVICE"
	])
	selectItemTypeMenuConditions[browsableObjects.NetworkResource]=[]
	selectItemTypeMenuConditions[browsableObjects.NetworkResource].extend([
		"FILE_RENAME",
		"TOOL_EJECT_DRIVE",
		"TOOL_EJECT_DEVICE",
		"READ_CONTENT_PREVIEW"
	])

	#それぞれFile・Folderと同期
	selectItemTypeMenuConditions[browsableObjects.SearchedFile]=selectItemTypeMenuConditions[browsableObjects.File]
	selectItemTypeMenuConditions[browsableObjects.SearchedFolder]=selectItemTypeMenuConditions[browsableObjects.Folder]

	#以下３つは専用のタブになってるのでこの機能でやる必要はない。KeyErrorにならないようにしとくだけ。
	selectItemTypeMenuConditions[browsableObjects.GrepItem]=[]
	selectItemTypeMenuConditions[browsableObjects.Drive]=[]
	selectItemTypeMenuConditions[browsableObjects.Stream]=[]
	selectItemTypeMenuConditions[browsableObjects.PastProgressItem]=[]
	selectItemTypeMenuConditions[browsableObjects.PastProgressHeader]=[]

	def __init__(self,environment):
		self.selectItemMenuConditions=[]
		for i in selectItemMenuConditions:
			self.selectItemMenuConditions.append(copy.copy(i))
		self.task=None
		self.colums=[]#タブに表示されるカラムの一覧。外からは読み取りのみ。
		self.listObject=None#リストの中身を保持している listObjects のうちのどれかのオブジェクト・インスタンス
		self.type=None
		self.isRenaming=False
		globalVars.app.config.add_section(self.__class__.__name__)
		self.environment=environment		#このタブ特有の環境変数
		self.stopSoundHandle=None
		self.checkedItem=set()
		self.hilightIndex=-1
		self.sortTargetColumnNo=None		#並び替え対象としてアイコン表示中のカラム番号
		if self.environment=={}:
			self.environment["markedPlace"]=None		#マークフォルダ
			self.environment["selectedItemCount"]=None	#選択中のアイテム数。0or1or2=2以上。
			self.environment["selectingItemCount"]={}	#選択中アイテムの種類(browsableObjects)毎の個数
			self.environment["listType"]=None			#表示中のリストタイプ(listObject)
			self.environment["history"]=history.History()#ディレクトリ移動の履歴

	def SetEnvironment(self,newEnv):
		"""タブの引継ぎなどの際にenvironmentの内容をコピーするために利用"""
		self.environment=newEnv

	def Initialize(self,parent,creator,existing_listctrl=None):
		"""タブを初期化する。親ウィンドウの上にリストビューを作るだけ。existing_listctrl にリストコントロールがある場合、そのリストコントロールを再利用する。"""
		self.log=logging.getLogger("falcon.%s" % self.__class__.__name__)
		self.log.debug("Created.")
		self.parent=parent
		self.InstallListCtrl(creator,existing_listctrl)
		self.background_tasks=[]

	def InstallListCtrl(self,creator,existing_listctrl=None):
		"""指定された親パネルの子供として、このタブ専用のリストコントロールを生成する。"""
		if existing_listctrl is None:
			self.hListCtrl=creator.ListCtrl(1,wx.EXPAND,style=wx.LC_REPORT | wx.LC_EDIT_LABELS | wx.LC_ALIGN_LEFT)
			creator.GetPanel().Layout()
		else:
			self.hListCtrl=existing_listctrl
		#end リストコントロールを再利用する

		#D&Dの受け入れ
		self.hListCtrl.SetDropTarget(DropTarget(self))

		self.hListCtrl.Bind(wx.EVT_LIST_COL_CLICK,self.col_click)
		self.hListCtrl.Bind(wx.EVT_LIST_COL_END_DRAG,self.col_resize)
		self.hListCtrl.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT,self.OnLabelEditStart)
		self.hListCtrl.Bind(wx.EVT_LIST_END_LABEL_EDIT,self.OnLabelEditEnd)
		self.hListCtrl.Bind(wx.EVT_LIST_ITEM_FOCUSED,self.ItemFocused)
		self.hListCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED,self.ItemSelected)
		self.hListCtrl.Bind(wx.EVT_LIST_ITEM_DESELECTED,self.ItemDeSelected)
		self.hListCtrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED,self.EnterItem)
		self.hListCtrl.Bind(wx.EVT_KEY_DOWN,self.KeyDown)
		self.hListCtrl.Bind(wx.EVT_MOUSE_EVENTS,self._MouseEvent)
		self.hListCtrl.Bind(wx.EVT_LIST_BEGIN_DRAG,self.BeginDrag)
		self.hListCtrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK,self.OpenContextMenu)
		self.hListCtrl.Bind(wx.EVT_MENU, self.CloseContextMenu)
		self.hListCtrl.Bind(wx.EVT_KILL_FOCUS, self._LostFocus)

	#表示されている順序でカラムの名前のリストを返す
	def GetListColumns(self):
		columnNames=list(self.listObject.columns.keys())
		ret=[]
		for i in self.hListCtrl.GetColumnsOrder():
			ret.append(columnNames[i])
		return ret

	def GetColumnOrderList(self):
		return self.hListCtrl.GetColumnsOrder()

	def SetColumnOrderList(self,l):
		self.hListCtrl.SetColumnsOrder(l)
		self.hListCtrl.Refresh()		#表示を更新する必要がある

	def GetItems(self):
		"""タブのリストの中身を取得する。"""
		return self.listObject.GetItems() if self.listObject is not None else []

	def GetFocusedItem(self):
		"""現在フォーカスが当たっているアイテムのインデックス番号を取得する。"""
		return self.hListCtrl.GetFocusedItem()

	def Focus(self,index,refresh=True):
		if refresh:
			self.hListCtrl.Select(-1,0)
		self.hListCtrl.Focus(index)
		if index!=-1:
			self.hListCtrl.Select(index)

	def GetFocusedElement(self):
		"""現在フォーカスが当たっているアイテムをbrowsableObjectsで返す"""
		if self.GetFocusedItem()<0:
			return None
		return self.listObject.GetElement(self.GetFocusedItem())

	def IsItemSelected(self,index=-1):
		if index>=0:
			return index in self.GetSelectedItems(True)
		else:
			# 選択されているアイテムが１つ以上存在するか否か
			return self.GetSelectedItemCount()>0

	def GetRootObject(self):
		"""ドライブ詳細情報表示で用いる"""
		return None


	def GetSelectedItemCount(self):
		return len(self.GetSelectedItems(True))

	def _GetSelectedItems(self,index_mode=False):
		"""
			チェックを加味せず、リストで選択されているアイテムを取得
		"""
		lst=[]
		next=self.hListCtrl.GetFirstSelected()
		while(next>=0):
			if index_mode:
				lst.append(next)
			else:
				elem=self.listObject.GetElement(next)
				lst.append(elem)
			next=self.hListCtrl.GetNextSelected(next)
		#end while
		if index_mode:
			return lst

		#リストを作る
		r=type(self.listObject)()
		r.Initialize(lst)
		return r

	def GetSelectedItems(self,index_mode=False):
		"""
			選択中のアイテムを、 ListObject で帰す
			index_mode が true の場合、 リスト上での index のリストを返す
			チェックされているアイテムがあればチェック中のアイテム、なければ選択状態の項目を取得
		"""
		if self.hasCheckedItem():	#選択は加味されず、チェックのみ
			lst=[]
			if index_mode:
				for item in self.checkedItem:
					lst.append(self.listObject.GetItemIndex(item))
				lst.sort()
				return lst
			lst=list(self.checkedItem)
			#lst=list(dict.fromkeys(lst))

			#リストを作る
			r=type(self.listObject)()
			r.Initialize(lst)
			r.ApplySort()		#元がsetなので順不同。必ず必要。
			return r
		else:
			return self._GetSelectedItems(index_mode)
		#end GetSelectedItems

	def GetListCtrl(self):
		return self.hListCtrl

	def SetListColumns(self,lst):
		"""リストコントロールにカラムを設定する。"""
		#カラム幅を保存し、いったん全ての列を削除
		self._updateColumnConfig()
		self.hListCtrl.DeleteAllColumns()
		self.sortTargetColumnNo=None

		col=lst.GetColumns()
		i=0
		for elem,format in col.items():
			#カラム幅の設定を取得
			w=globalVars.app.config.getint(lst.__class__.__name__,"column_width_"+str(i),100,0,1500)

			#カラムを作成
			self.hListCtrl.InsertColumn(i,elem,format=format,width=w)
			#column=self.hListCtrl.GetColumn(i)
			#column.SetBackgroundColour("ff0000")
			#self.hListCtrl.SetColumn(i,column)
			i+=1
		#end カラムを作る

		#カラムの並び替え設定を反映
		try:
			self.hListCtrl.SetColumnsOrder(json.loads(globalVars.app.config[lst.__class__.__name__]["columns_order"]))
		except (json.decoder.JSONDecodeError,TypeError):
			self._updateColumnConfig(type(lst))		#configが壊れているので初期値リセット
	#end SetListColumns

	def Update(self,lst,cursor=-1):
		"""指定された要素をタブに適用する。"""
		self.DeleteAllItems()		#先に消しておかないとカラム数が合わない画面がユーザに見えてしまう
		if type(lst)!=type(self.listObject):
			self.SetListColumns(lst)
		if self.environment["history"].isEmpty():			#タブ作成時のみ
			self.environment["history"].add(lst.rootDirectory)
		self.listObject=lst
		self.environment["listType"]=type(lst)
		self.UpdateListContent(self.listObject.GetItemList())

		self.Focus(cursor)

		#タブの名前変更を通知
		globalVars.app.hMainView.UpdateTabName()

	def UpdateListContent(self,content):
		"""
			リストコントロールの中身を更新し、並び替え状況を示すアイコンを再配置する。
			カラムの数やテキストは変更しない。
		"""
		self.log.debug("Updating list control...")
		self.DeleteAllItems()

		t=misc.Timer()
		for elem in content:
			self._AppendElement(elem)
		#end 追加
		self.log.debug("List control updated in %f seconds." % t.elapsed)

	def _AppendElement(self,elem,index=-1):
		"""
			browsableObjectを指定して、リストに追加する
			indexは検索結果一覧でフォルダを正しい位置に挿入するために利用
		"""
		if index>=0:
			index=self.hListCtrl.InsertItem(index,"")
			i=0
			for text in elem.GetListTuple():
				self.hListCtrl.SetItem(index,i,text)
				i+=1
		else:
			index=self.hListCtrl.Append(elem.GetListTuple())
		if elem.hIcon>=0:
			iconIndex=self.GetIconIndex(elem.hIcon)
			if iconIndex>=0:
				self.hListCtrl.SetItemImage(index,iconIndex,iconIndex)

	def GetIconIndex(self,hIcon):
		"""同じhIconから作ったアイコンをImageListに複数追加しようとするとエラーとなるので対策。"""
		if hIcon in self.iconNumbers:
			return self.iconNumbers[hIcon]
		else:
			icon=wx.Icon()
			if icon.CreateFromHICON(hIcon):
				iconIndex=self.hIconList.Add(icon)
				self.iconNumbers[hIcon]=iconIndex
				return iconIndex
			return -1

	def _InitIconList(self):
		"""listCtrlにアイコン設定する準備"""
		if self.listObject==None:
			return
		self.hIconList=wx.ImageList(32,32,False,len(self.listObject))
		self.hListCtrl.AssignImageList(self.hIconList,wx.IMAGE_LIST_SMALL)
		self.iconNumbers={}

		#カラム用アイコンを登録
		self.hIconList.Add(wx.Icon("fx/dummy.ico"))
		self.hIconList.Add(wx.Icon("fx/ascending.ico"))
		self.hIconList.Add(wx.Icon("fx/descending.ico"))
		self._SetSortIcon()

	def _SetSortIcon(self):
		#アイコンを設定済みならいったん削除
		if self.sortTargetColumnNo!=None:
			self.hListCtrl.SetColumnImage(self.sortTargetColumnNo,0)

		#並び替え状況に応じてアイコン設定
		self.hListCtrl.SetColumnImage(self.listObject.sortCursor,1+self.listObject.sortDescending)
		self.sortTargetColumnNo=self.listObject.sortCursor

	def MakeShortcut(self,option):
		prm=""
		dir=""
		if option["type"]=="shortcut":
			prm=option["parameter"]
			dir=option["directory"]
		target=self.GetFocusedElement().fullpath
		dest=option["destination"]
		if not os.path.isabs(dest):	#早退の場合は絶対に直す
			dest=os.path.normpath(os.path.join(os.path.dirname(target),dest))

		#シンボリックリンクはNTFSにしか作成できない
		if option["type"]=="symbolicLink":
			tmp=misc.GetRootObject(dest)
			if (not tmp) or type(fileSystemManager.GetFileSystemObject(tmp.fullpath))!=fileSystemManager.NTFS:
				dialog(_("エラー"),_("NTFSドライブ以外の場所にシンボリックリンクを作成することはできません。"))
				return False

		#ハードリンクの場合、同一ドライブ上への作成に限られる
		#ネットワーク上の項目への作成はここにくる以前でブロック済み
		if option["type"]=="hardLink":
			if target[0]!=dest[0]:	#異なるドライブへの作成
				dialog(_("エラー"),_("他のドライブに対してハードリンクを作成することはできません。"))
				return False

		if option["type"]=="shortcut":
			inst={"operation":option["type"], "target": [(dest,target,prm,dir,option["linkType"]==1)]}
		else:
			inst={"operation":option["type"], "from": [target], "to": [dest], "relative":option["linkType"] }
		#end ショートカットかそれ以外
		op=fileOperator.FileOperator(inst)
		ret=op.Execute()
		if op.CheckSucceeded()==0:
			dialog(_("エラー"),_("ショートカットの作成に失敗しました。"))
			return False
		#end error
		self.UpdateFilelist(silence=True)
		return True

	def MakeDirectory(self):
		return errorCodes.NOT_SUPPORTED#基底クラスではなにも許可しない

	def PastOperation(self,target,dest,op):
		return errorCodes.NOT_SUPPORTED#基底クラスではなにも許可しない

	def Trash(self):
		return errorCodes.NOT_SUPPORTED#基底クラスではなにも許可しない

	def Delete(self):
		return errorCodes.NOT_SUPPORTED#基底クラスではなにも許可しない

	def ChangeAttribute(self,attrib_checks):
		return errorCodes.NOT_SUPPORTED#基底クラスではなにも許可しない

	def Copy(self):
		return errorCodes.NOT_SUPPORTED#基底クラスではなにも許可しない

	def Cut(self):
		return errorCodes.NOT_SUPPORTED#基底クラスではなにも許可しない

	def GoToTopFile(self):
		return errorCodes.NOT_SUPPORTED#基底クラスではなにも許可しない

	def ShowProperties(self):
		index=self.GetFocusedItem()
		try:
			shell.ShellExecuteEx(shellcon.SEE_MASK_INVOKEIDLIST,0,"properties",self.listObject.GetElement(index).fullpath)
		except pywintypes.error as e:
			if e.winerror==1223:		#'この操作はユーザーによって取り消されました。'で、ネットワーク接続失敗などで発生
				pass
			else:
				raise e

	def Jump(self,direction):
		cursor=self.listObject.Jump(self.GetFocusedItem(),direction)
		if cursor!=-1:
			self.Focus(cursor,True)

	def GoHistNext(self):
		if not self.environment["history"].hasNext():
			return errorCodes.BOUNDARY
		ret=self.Move(self.environment["history"].getNext(),addHistory=False)
		return ret

	def GoHistPrevious(self):
		if not self.environment["history"].hasPrevious():
			return errorCodes.BOUNDARY
		ret=self.Move(self.environment["history"].getPrevious(),addHistory=False)
		return ret

	def KeyDown(self,event):
		"""キーが押されたらここにくる。"""
		self.StopSound()
		event.Skip()

	def _IsItemChecked(self,elem):
		"""
			browsableObjectsから、そのアイテムがチェック状態か否かを調べる
			外からはSelectと合わせて調べる必要性以外にないはずなのでprivate
		"""
		return elem in self.checkedItem

	def OnSpaceKey(self):
		"""spaceキー押下時、アイテムをチェック/チェック解除する"""
		self.ItemMarkProcess([self.GetFocusedElement()])

	def CheckAll(self):
		self.ItemMarkProcess(self.listObject.GetItemList(),True)
		globalVars.app.say(_("すべてチェック"), interrupt=True)

	def UncheckAll(self):
		self.ItemMarkProcess(self.listObject.GetItemList(),False)
		globalVars.app.say(_("すべてチェック解除"), interrupt=True)

	def CheckInverse(self):
		self.ItemMarkProcess(self.listObject.GetItemList())
		globalVars.app.say(_("チェック反転"), interrupt=True)

	def ItemMarkProcess(self,items,strict=None):
		"""
			itemsをチェック・チェック解除する。現在状態と比べて反転させる
			strict!=Noneの時は、全アイテムのチェック状態をstrictに合わせる
		"""
		for item in items:
			index=self.listObject.GetItemIndex(item)
			if strict==False or (strict==None and self._IsItemChecked(item)):
				#チェック解除
				self.checkedItem.discard(item)
				if len(items)==1 and strict==None:
					globalVars.app.say(_("チェック解除"), interrupt=True)
				self.hListCtrl.SetItemBackgroundColour(index,"#000000")
			else:				#チェック
				if len(items)==1:
					globalVars.app.say(_("チェック"), interrupt=True)
					if not strict:
						globalVars.app.PlaySound(globalVars.app.config["sounds"]["check"])
				self.checkedItem.add(item)
				self.hListCtrl.SetItemBackgroundColour(index,"#0000FF")
				self.hListCtrl.RefreshItem(index)
			#カーソルを１つ下へ移動
			if len(items)==1 and index!=len(self.listObject)-1:		#カーソルが一番下以外にある時
				#self.hListCtrl.SetItemState(item,0,wx.LIST_STATE_SELECTED)
				self.Focus(index+1,True)
		self.hListCtrl.Update()
		globalVars.app.hMainView.menu.Enable(menuItemsStore.getRef("EDIT_UNMARKITEM_ALL"),self.hasCheckedItem())
		globalVars.app.hMainView.menu.Enable(menuItemsStore.getRef("EDIT_MARKITEM_ALL"),len(self.checkedItem)!=len(self.listObject))

	def BeginDrag(self,event):
		data=wx.FileDataObject()
		for f in self.GetSelectedItems():
			data.AddFile(f.fullpath)

		itemImage=self.hListCtrl.GetImageList(wx.IMAGE_LIST_SMALL).GetBitmap(
				self.hListCtrl.GetItem(self.GetSelectedItems(True)[0]).GetImage()
			).ConvertToImage().Scale(128,128).ConvertToBitmap()

		i=wx.DragImage(itemImage)
		i.BeginDrag((16,16),globalVars.app.hMainView.hFrame,True,None)

		obj=DropSource(data,globalVars.app.hMainView.hFrame)
		obj.hImage=i
		i.Show()
		obj.GiveFeedback(None)		#座標の計算などをしてi.Moveが呼ばれる
		obj.DoDragDrop()
		i.EndDrag()

	def SelectAll(self):
		if self.hasCheckedItem():	#チェックアイテムがある場合は実行不可
			globalVars.app.PlaySound(globalVars.app.config["sounds"]["boundary"])
			return errorCodes.BOUNDARY
		globalVars.app.say(_("全て選択"), interrupt=True)
		for i in range(self.hListCtrl.GetItemCount()):
			self.hListCtrl.Select(i)
		return True

	def NameCopy(self):
		globalVars.app.say(_("ファイル名をコピー"), interrupt=True)
		t=self.GetSelectedItems().GetItemNames()
		t="\n".join(t)
		with clipboardHelper.Clipboard() as c:
			c.set_unicode_text(t)

	def FullpathCopy(self):
		t=self.GetSelectedItems().GetItemPaths()
		globalVars.app.say(_("フルパスをコピー"), interrupt=True)
		t="\n".join(t)
		with clipboardHelper.Clipboard() as c:
			c.set_unicode_text(t)

	def UpdateFilelist(self,silence=False,cursorTargetName=""):
		"""同じリストで、内容を再取得して更新する。"""
		if silence==False:
			globalVars.app.say(_("更新"), interrupt=True)
		if cursorTargetName=="":
			item=self.GetFocusedElement()
		result=self.listObject.Update()
		if result != errorCodes.OK:
			return result			#アクセス負荷など
		self.OnUpdate()
		cursor=-1
		if cursorTargetName=="":
			if item!=None:
				cursor=self.listObject.Search(item.basename,0)
		else:
			cursor=self.listObject.Search(cursorTargetName,0)
		#end ターゲットが指定されているかどうか
		self.Update(self.listObject,cursor)

	def OnUpdate(self):
		"""リスト更新時のみ、更新後に呼ばれる"""
		pass

	def SortCycleAd(self):
		"""昇順と降順を交互に切り替える。"""
		self.listObject.SetSortDescending(self.listObject.GetSortDescending()==0)
		self.ApplySort()

	def SortSelect(self):
		"""並び順を指定する。"""
		m=wx.Menu()
		s=self.listObject.GetSupportedSorts()
		i=0
		for elem in s:
			m.Append(i,lists.GetSortDescription(elem))
			i+=1
		#end 追加
		item=self.hListCtrl.GetPopupMenuSelectionFromUser(m)
		m.Destroy()
		self.listObject.SetSortCursor(item)
		self.ApplySort()

	def _updateConfig(self):
		"""ソートの設定をconfigに反映する。"""
		s=self.listObject.__class__.__name__
		globalVars.app.config[s]["sorting"]=self.listObject.GetSortCursor()
		globalVars.app.config[s]["descending"]=int(self.listObject.GetSortDescending())

	def _updateColumnConfig(self,listType=None):
		"""カラムのソート状態をconfigに保存する。"""
		if listType==None:
			listType=self.environment["listType"]
		value=self.hListCtrl.GetColumnsOrder()
		if value==[]:return		#起動直後で、まだカラム生成前
		key=listType.__name__
		globalVars.app.config[key]["columns_order"]=str(value)

	def col_resize(self,event):
		no=event.GetColumn()
		width=self.hListCtrl.GetColumnWidth(no)
		globalVars.app.config[self.listObject.__class__.__name__]["column_width_"+str(no)]=str(width)

	def col_click(self,event):
		no=event.GetColumn()
		if self.listObject.GetSortCursor()==no:
			self.listObject.SetSortDescending(self.listObject.GetSortDescending()==0)
		else:
			self.listObject.SetSortCursor(no)
		self.ApplySort()

	def SortNext(self):
		self.listObject.SetSortCursor()
		self.ApplySort()

	def ApplySort(self):
		self._updateConfig()				#設定の保存
		old=self.listObject.GetItemList()	#ソート前の並び順のリスト
		self.listObject.ApplySort()			#リストオブジェクト側をソート
		new=self.listObject.GetItemList()	#ソート後の並び順のリスト

		#オブジェクトにソート後のインデックスの番号を付ける
		for i in range(self.hListCtrl.GetItemCount()):
			self.hListCtrl.SetItemData(i,new.index(old[i]))

		#リストをソートする
		self.hListCtrl.SortItems(self._compare)

		#画面上のソートアイコンを設定
		self._SetSortIcon()

	def _compare(self, item1, item2):
		"""リストのソートでlistObjectから呼ばれる"""
		return item1>item2

	def _cancelBackgroundTasks(self):
		"""フォルダ容量計算など、バックグラウンドで走っていて、ファイルリストが更新されるといらなくなるようなものをキャンセルする。"""
		for elem in self.background_tasks:
			elem.Cancel()
		#end for
		self.background_tasks=[]

	def EnterItem(self,event):
		"""forward アクションを実行する。"""
		globalVars.app.hMainView.events.GoForward()

	def Move(self,path,cursor="",addHistory=True):
		"""指定の場所へ移動する。"""
		if addHistory:
			self.environment["history"].add(path)
			self.parent.menu.Enable(menuItemsStore.getRef("MOVE_HIST_NEXT"),self.environment["history"].hasNext())
			self.parent.menu.Enable(menuItemsStore.getRef("MOVE_HIST_PREV"),self.environment["history"].hasPrevious())
		r=navigator.Navigate(path,cursor,previous_tab=self,environment=self.environment)
		return errorCodes.OK if r is self else r

	def GoForward(self,stream,admin=False):
		"""選択中のフォルダやドライブに入るか、選択中のファイルを実行する。stream=True の場合、ファイルの NTFS 副ストリームを開く。"""
		index=self.GetFocusedItem()
		elem=self.listObject.GetElement(index)
		if (not stream) and (type(elem)==browsableObjects.File):	#このファイルを開く
			misc.RunFile(elem.fullpath,admin,"",self.listObject.rootDirectory)
			return
		else:
			#TODO: 管理者権限が要求され、自身が管理者権限を有していないなら、別のfalconが昇格して開くように
			return self.Move(elem.fullpath)
		#end ファイルを開くか移動するか
	#end GoForward

	def GoBackward(self):
		"""内包しているフォルダ/ドライブ一覧へ移動する。"""
		self.StopSound()
		if len(self.listObject.rootDirectory)<=3:		#ドライブリストへ
			target=""
			cursorTarget=self.listObject.rootDirectory[0]
		else:
			root=self.listObject.rootDirectory
			while(True):
				if len(self.listObject.rootDirectory)<3:		#ドライブリストへ
					target=""
					cursorTarget=self.listObject.rootDirectory[0]
					break
				#end 下がっていってドライブリスト
				spl=os.path.split(root)
				target=spl[0]
				if(target==root and root[0:2]=="\\\\"):
					#\\hoge\\fuga　の階層のみ、os.path.split()しても結果が変わらない
					target=re.sub("(\\\\\\\\[^\\\\]+).+","\\1",target)
					cursorTarget=re.sub("\\\\\\\\[^\\\\]+(.+)","\\1",target)
					result=self.Move(target,cursorTarget)
					if(type(result)!=int):
						return result
					else:
						cursorTarget=target
						target=""
				elif os.path.isdir(target):
					cursorTarget=spl[1]
					break
				#end 移動先が存在するので抜ける
				root=target
			#end フォルダがアルマで下がる
		#end ドライブリスト直行かそうでないか
		return self.Move(target,cursorTarget)

	def MarkSet(self):
		"""現在開いている場所をマークする"""
		globalVars.app.say(_("マーク設定"), interrupt=True)
		self.environment["markedPlace"]=self.listObject.rootDirectory
		self.log.debug("markset at \""+self.environment["markedPlace"] + "\"")

	def GoToMark(self):
		"""マークした場所へ移動する"""
		ret=self.Move(self.environment["markedPlace"])
		if ret!=errorCodes.OK:
			return ret
		globalVars.app.say(_("マーク位置へ移動"), interrupt=True)
		return errorCodes.OK

	def StartRename(self):
		index=self.GetFocusedItem()
		self.hListCtrl.EditLabel(index)

	def OnLabelEditStart(self,evt):
		self.isRenaming=True
		self.parent.SetShortcutEnabled(False)

	def IsMarked(self):
		return self.environment["markedPlace"]!=None

	def hasCheckedItem(self):
		return len(self.checkedItem)>0

	def DeleteAllItems(self):
		"""
			必用な調整を経て、リストビューを空にする
			別途listObjectについては処理が必要
		"""
		self._cancelBackgroundTasks()
		self.hListCtrl.DeleteAllItems()
		self.checkedItem=set()
		self.hilightIndex=-1
		self.ItemSelected()			#メニューバーのアイテムの状態更新処理。選択中アイテムがいったん0になってるため必要
		globalVars.app.hMainView.menu.Enable(menuItemsStore.getRef("EDIT_UNMARKITEM_ALL"),False)
		globalVars.app.hMainView.menu.Enable(menuItemsStore.getRef("EDIT_MARKITEM_ALL"),True)
		self.hilightIndex=-1
		self._InitIconList()

	def ItemFocused(self,event):
		#チェック機能仕様中の複数選択は不可
		if self.hasCheckedItem() and self.hListCtrl.GetSelectedItemCount()>1:
			selectedItems=self._GetSelectedItems(True)
			for i in selectedItems:
				if i!=event.GetIndex():
					#print("--------")
					#print(event.GetIndex())
					#print(self._GetSelectedItems(True))
					self.hListCtrl.Select(i,0)
					#print(self._GetSelectedItems(True))
					#print("--------")
		#チェック状態のアイテムなら音を鳴らす
		if self._IsItemChecked(self.listObject.GetElement(event.GetIndex())):
			globalVars.app.PlaySound(globalVars.app.config["sounds"]["checked"])
		event.Skip()

	def ItemSelected(self,event=None):
		"""リストビューのアイテムの選択時に呼ばれる"""

		#個数ベースでのメニューのロック・アンロック
		c=self.GetSelectedItemCount()
		if c>2:c=2
		#print(str(self.environment["selectedItemCount"])+"=>"+str(c))
		if self.environment["selectedItemCount"]!=c:
			if self.environment["selectedItemCount"]!=None:
				globalVars.app.hMainView.menu.UnBlock(self.selectItemMenuConditions[self.environment["selectedItemCount"]])
			globalVars.app.hMainView.menu.Block(self.selectItemMenuConditions[c])
			self.environment["selectedItemCount"]=c

		#種類ベースでのメニューのロック
		if event:		#アイテムが選択された
			#チェック済みアイテムなら何もしない
			if self._IsItemChecked(self.listObject.GetElement(event.GetIndex())):
				return
			elem=self.listObject.GetElement(event.GetIndex())
			try:
				self.environment["selectingItemCount"][elem.__class__]+=1
			except KeyError:
				self.environment["selectingItemCount"][elem.__class__]=1
			if self.environment["selectingItemCount"][elem.__class__]==1:	#新規ブロック
				globalVars.app.hMainView.menu.Block(self.selectItemTypeMenuConditions[elem.__class__])
		else:	#ビューを再描画した場合など
			#全部の選択をなかったことにする
			for i,v in self.environment["selectingItemCount"].items():
				if v>0:
					self.environment["selectingItemCount"][i]=0
					globalVars.app.hMainView.menu.UnBlock(self.selectItemTypeMenuConditions[i])
			#選択中アイテムの状況を取得して処理する
			if not self.IsItemSelected():
				return
			for elem in self.GetSelectedItems():
				try:
					self.environment["selectingItemCount"][elem.__class__]+=1
				except KeyError:
					self.environment["selectingItemCount"][elem.__class__]=1
				if self.environment["selectingItemCount"][elem.__class__]==1:	#新規ブロック
					globalVars.app.hMainView.menu.Block(self.selectItemTypeMenuConditions[elem.__class__])

	def ItemDeSelected(self,event=None,index=0):
		#個数ベースでのメニューのロック・アンロック
		c=self.GetSelectedItemCount()
		if c>2:c=2
		#print(str(self.environment["selectedItemCount"])+"=>"+str(c))
		if self.environment["selectedItemCount"]!=c:
			if self.environment["selectedItemCount"]!=None:
				globalVars.app.hMainView.menu.UnBlock(self.selectItemMenuConditions[self.environment["selectedItemCount"]])
			globalVars.app.hMainView.menu.Block(self.selectItemMenuConditions[c])
			self.environment["selectedItemCount"]=c

		#種類ベースでのメニューのアンロック
		if event:
			#チェック状態なら何もしない
			if self.IsItemSelected(event.GetIndex()):
				return
			elem=self.listObject.GetElement(event.GetIndex())
		else:
			elem=self.listObject.GetElement(index)
		try:
			self.environment["selectingItemCount"][elem.__class__]-=1
			if self.environment["selectingItemCount"][elem.__class__]==0:	#ブロック解除
				globalVars.app.hMainView.menu.UnBlock(self.selectItemTypeMenuConditions[elem.__class__])
		except KeyError:
			self.environment["selectingItemCount"][elem.__class__]=0

	def _appendContextMenu(self,hMenu,elem):
		if elem['type']=="separator":
			hMenu.AppendSeparator()
		if 'submenu' in elem:
			hSubMenu=wx.Menu()
			hMenu.AppendSubMenu(hSubMenu,elem['name'])
			for elem2 in elem['submenu']:
				self._appendContextMenu(hSubMenu,elem2)
			#end for
			return
		#end has sub menu
		hMenu.Append(elem['id'],elem['name'])

	def OpenContextMenu(self,event):
		if event:	#マウス操作
				x,y=wx.GetMousePosition()
		else:
				rect=self.hListCtrl.GetItemRect(self.GetFocusedItem(),wx.LIST_RECT_LABEL)
				x,y=self.hListCtrl.ClientToScreen(rect.GetBottomRight())
		#end 表示位置判定

		RegisterMenuCommand=globalVars.app.hMainView.menu.RegisterMenuCommand

		targetPaths=self.GetSelectedItems().GetItemPaths()
		misc.GetContextMenu()
		misc.AddCustomContextMenuItem("テスト",5001)
		can_show_menu=misc.AddContextMenuItemsFromWindows(targetPaths)
		if not can_show_menu:
			misc.DestroyContextMenu()
			return#コンテキストメニュー生成できなかった
		#end メニュー生成できない
		cmd=misc.ShowContextMenu(x,y)
		evt=wx.MenuEvent(id=cmd)
		self.CloseContextMenu(evt)

	def CloseContextMenu(self,event):
		selected=event.GetId()							#メニュー識別子の数値

		if selected>=5000:
			event.Skip()
		else:
			misc.ExecContextMenuItem(selected)
			misc.DestroyContextMenu()
		#end exec context menu action

	def ReadCurrentFolder(self):
		return errorCodes.NOT_SUPPORTED

	def Preview(self):
		ext=self.GetFocusedElement().fullpath.split(".")[-1].lower()
		if ext in constants.SUPPORTED_AUDIO_FORMATS:
			self.StopSound()
			ret=globalVars.app.PlaySound(self.GetFocusedElement().fullpath,custom_location=True,volume=globalVars.app.config.getint("preview","audio_volume",100,1,300))
			if ret==-1:
				dialog(_("エラー"),_("再生に失敗しました。ファイルにアクセスができないか、ファイルが壊れている可能性があります。"))
				return errorCodes.FILE_NOT_FOUND
			self.stopSoundHandle=ret
		elif misc.isDocumentExt(ext):
			globalVars.app.say(misc.ExtractText(self.GetFocusedElement().fullpath), interrupt=True)
		else:
			globalVars.app.say(_("プレビューに対応していないファイル形式です。"), interrupt=True)

	def ReadHeader(self):
		ext=self.GetFocusedElement().fullpath.split(".")[-1].lower()
		if not misc.isDocumentExt(ext):
			globalVars.app.say(_("ドキュメントファイルではありません。"), interrupt=True)
			return
		#end 非対応
		ln=globalVars.app.config.getint("preview","header_line_count",10,1,100)
		s=misc.ExtractText(self.GetFocusedElement().fullpath).split("\n")
		if len(s)>ln: s=s[0:ln]
		prefix=_("先頭%(ln)d行") % {'ln': ln}
		globalVars.app.say("%s %s" % (prefix,"\n".join(s)), interrupt=True)

	def ReadFooter(self):
		ext=self.GetFocusedElement().fullpath.split(".")[-1].lower()
		if not misc.isDocumentExt(ext):
			globalVars.app.say(_("ドキュメントファイルではありません。"), interrupt=True)
			return
		#end 非対応
		ln=globalVars.app.config.getint("preview","footer_line_count",10,1,100)
		s=misc.ExtractText(self.GetFocusedElement().fullpath).split("\n")
		if len(s)>10: s=s[-10:]
		prefix=_("末尾%(ln)d行") % {'ln': ln}
		globalVars.app.say("%s %s" % (prefix,"\n".join(s)), interrupt=True)

	def ReadListItemNumber(self,short=False):
		return errorCodes.NOT_SUPPORTED

	def ReadListInfo(self):
		return errorCodes.NOT_SUPPORTED

	def SetMovementRead(self):
		m=wx.Menu()
		m.AppendCheckItem(0,_("フォルダ階層を読み上げ"))
		m.AppendCheckItem(1,_("フォルダ名を読み上げ"))
		m.AppendCheckItem(2,_("項目数を読み上げ"))
		m.Check(0,globalVars.app.config.getboolean('on_list_moved','read_directory_level',True))
		m.Check(1,globalVars.app.config.getboolean('on_list_moved','read_directory_name',True))
		m.Check(2,globalVars.app.config.getboolean('on_list_moved','read_item_count',True))
		item=self.hListCtrl.GetPopupMenuSelectionFromUser(m)
		globalVars.app.config['on_list_moved']['read_directory_level']=m.IsChecked(0)
		globalVars.app.config['on_list_moved']['read_directory_name']=m.IsChecked(1)
		globalVars.app.config['on_list_moved']['read_item_count']=m.IsChecked(2)

	def ExecProgram(self,val):
		argv=misc.CommandLineToArgv(val)
		path=argv[0]
		prm=" ".join(argv[1:])
		misc.RunFile(path,prm=prm,workdir=self.listObject.rootDirectory)

	def OnBeforeChangeTab(self):
		"""タブ切り替えが起きる前に呼ばれる。"""
		self.StopSound()
		self._updateColumnConfig()

	def OnClose(self):
		"""タブが閉じられる前に呼び出される。検索結果タブでは、検索中にタブが閉じられたとき、検索のための非同期処理のキャンセルを待機しなければならない。"""
		pass

	def _LostFocus(self,event=None):
		self.StopSound()

	def _MouseEvent(self,event):
		if event.GetEventType() not in (wx.wxEVT_MOTION,wx.wxEVT_ENTER_WINDOW,wx.wxEVT_LEAVE_WINDOW,wx.wxEVT_MOUSEWHEEL):
			self.StopSound()
		event.Skip()


	def StopSound(self):
		if self.stopSoundHandle is not None:#音を鳴らしてたので止める
			globalVars.app.StopSound(self.stopSoundHandle)
			self.stopSoundHandle=None

	#D&Dで使うアイテムハイライト
	def Hilight(self,index):
		if index==-1:
			if self.hilightIndex>=0:
				self.hListCtrl.SetItemState(index,0,wx.LIST_STATE_DROPHILITED)
				self.hilightIndex=-1
		elif self.hilightIndex != index:
			self.hListCtrl.SetItemState(self.hilightIndex,0,wx.LIST_STATE_DROPHILITED)
			if isinstance(self.listObject.GetElement(index),(browsableObjects.Folder,browsableObjects.Drive)):
				self.hListCtrl.SetItemState(index,wx.LIST_STATE_DROPHILITED,wx.LIST_STATE_DROPHILITED)
				self.hilightIndex=index
			else:
				self.hilightIndex=-1

	def _findFocusAfterDeletion(self,paths,focus_index):
		"""
			ゴミ箱/削除して、ファイルリストを更新した後に呼び出す。
			削除語のカーソル位置を見つける。
		"""
		#カーソルをどこに動かすかを決定、まずはもともとフォーカスしてた項目があるかどうか
		if os.path.exists(paths[focus_index]):
			new_cursor_path=paths[focus_index]#フォーカスしてたファイル
		else:#あるファイルを上下に探索
			if len(paths)==1: return -1#もともと1個しかファイルがなくて、そのファイルが消えている場合、フォーカスは-1で確定する
			new_cursor_path=""
			ln=len(paths)
			i=1
			while(True):
				if i>focus_index and i>ln-focus_index-1: break#探索し尽くしたらやめる
				tmp=focus_index-i
				if tmp>=0 and os.path.exists(paths[tmp]):#あった
					new_cursor_path=paths[tmp]
					break
				#end 上
				tmp=focus_index+i
				if tmp<ln and os.path.exists(paths[tmp]):#あった
					new_cursor_path=paths[tmp]
					break
				#end 下
				i+=1
			#end 探索
		#end さっきフォーカスしてた項目がなくなってた
		#カーソルをどの項目に動かすか分かった
		focus_index=0
		for elem in self.listObject:
			if elem.fullpath==new_cursor_path: break
			focus_index+=1
		#end 検索
		return focus_index


class DropSource(wx.DropSource):
	def GiveFeedback(self,effect):
		self.hImage.Move(globalVars.app.hMainView.hFrame.ScreenToClient(wx.GetMousePosition()))
		return False


class DropTarget(wx.DropTarget):
	def __init__(self,parent):
		super().__init__(wx.FileDataObject())
		self.parent=parent			#tabが入る

	#マウスオーバー時に呼ばれる
	#まだマウスを放していない
	def OnDragOver(self,x,y,defResult):
		if not globalVars.app.hMainView.menu.IsEnable("EDIT_PAST"):
			return wx.DragResult.DragNone	#現在のビューでは受け入れ不可

		i,flg=self.parent.hListCtrl.HitTest((x,y))
		if flg & wx.LIST_HITTEST_ONITEM !=0:
			self.parent.Hilight(i)
		else:
			self.parent.Hilight(-1)
		return defResult

	#ドロップされずにマウスが外に出た
	#戻り値不要
	def OnLeave(self):
		self.parent.Hilight(-1)
		pass

	#マウスが放されたら呼ばれる
	#現在データの受け入れが可能ならTrue
	def OnDrop(self,x,y):
		self.parent.Hilight(-1)

		if not globalVars.app.hMainView.menu.IsEnable("EDIT_PAST"):
			return wx.DragResult.DragNone	#現在のビューでは受け入れ不可
		return not self.parent.isRenaming

	#データを受け入れ、結果を返す
	def OnData(self,x,y,defResult):
		index=-1
		i,flg=self.parent.hListCtrl.HitTest((x,y))
		if flg & wx.LIST_HITTEST_ONITEM !=0:
			index=i
		if index>=0 and isinstance(self.parent.listObject.GetElement(index),(browsableObjects.Folder,browsableObjects.Drive)):
			#カーソルのあるオブジェクトの中に入れる
			dest=self.parent.listObject.GetElement(index).fullpath
		else:
			dest=self.parent.listObject.rootDirectory
		self.GetData()
		self.parent.PastOperation(self.DataObject.GetFilenames(),dest)
		return defResult		#推奨されたとおりに返しておく
