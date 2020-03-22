# -*- coding: utf-8 -*-
#Falcon tab base object
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
タブは、必ずリストビューです。カラムの数と名前と、それに対応するリストの要素がタブを構成します。たとえば、ファイル一覧では「ファイル名」や「サイズ」などがカラムになり、その情報がリストに格納されています。ファイル操作の状況を示すタブの場合は、「進行率」や「状態」などがカラムの名前として想定されています。リスト上でエンターを押すことで、アクションを実行できます。ファイルビューではファイルやフォルダを開き、ファイル操作では問い合わせに応答することができます。
"""
import json
import logging
import os

import wx
import browsableObjects
import clipboardHelper
import errorCodes
import globalVars
import lists
import misc
from . import navigator

class FalconTabBase(object):
	"""全てのタブに共通する基本クラス。"""

	blockMenuList=[]
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
		"MOVE_FORWARD",
		"MOVE_FORWARD_ADMIN",
		"MOVE_FORWARD_TAB",
		"MOVE_FORWARD_STREAM",
		"TOOL_DIRCALC",
		"TOOL_HASHCALC",
		"TOOL_ADDPATH",
		"TOOL_EJECT_DRIVE",
		"TOOL_EJECT_DEVICE"
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
		"TOOL_DIRCALC",
		"TOOL_HASHCALC",
		"TOOL_EJECT_DRIVE",
		"TOOL_EJECT_DEVICE"
	])


	def __init__(self,environment):
		self.task=None
		self.colums=[]#タブに表示されるカラムの一覧。外からは読み取りのみ。
		self.listObject=None#リストの中身を保持している listObjects のうちのどれかのオブジェクト・インスタンス
		self.type=None
		self.isRenaming=False
		globalVars.app.config.add_section(self.__class__.__name__)
		self.environment=environment		#このタブ特有の環境変数
		if self.environment=={}:
			self.environment["markedPlace"]=None		#マークフォルダ
			self.environment["selectedItemCount"]=None	#選択中のアイテム数。0or1or2=2以上。

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
			self.hListCtrl=creator.ListCtrl(1,wx.EXPAND,style=wx.LC_REPORT|wx.LC_EDIT_LABELS)
			creator.GetPanel().Layout()
		else:
			self.hListCtrl=existing_listctrl
		#end リストコントロールを再利用する
		self.hListCtrl.Bind(wx.EVT_LIST_COL_CLICK,self.col_click)
		self.hListCtrl.Bind(wx.EVT_LIST_COL_END_DRAG,self.col_resize)
		self.hListCtrl.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT,self.OnLabelEditStart)
		self.hListCtrl.Bind(wx.EVT_LIST_END_LABEL_EDIT,self.OnLabelEditEnd)
		self.hListCtrl.Bind(wx.EVT_LIST_ITEM_SELECTED,self.ItemSelected)
		self.hListCtrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED,self.EnterItem)
		self.hListCtrl.Bind(wx.EVT_KEY_DOWN,self.KeyDown)
		self.hListCtrl.Bind(wx.EVT_LIST_BEGIN_DRAG,self.BeginDrag)
		self.hListCtrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK,self.OpenContextMenu)
		self.hListCtrl.Bind(wx.EVT_MENU, self.CloseContextMenu)

	def GetListColumns(self):
		return self.columns

	def GetItems(self):
		"""タブのリストの中身を取得する。"""
		return self.listObject.GetItems() if self.listObject is not None else []

	def GetFocusedItem(self):
		"""現在フォーカスが当たっているアイテムのインデックス番号を取得する。"""
		return self.hListCtrl.GetFocusedItem()

	def GetFocusedElement(self):
		"""現在フォーカスが当たっているアイテムをbrowsableObjectsで返す"""
		if self.GetFocusedItem()<0:
			return None
		return self.listObject.GetElement(self.GetFocusedItem())

	# 選択されているアイテムが１つ以上存在するか否か
	def IsItemSelected(self):
		return self.hListCtrl.GetSelectedItemCount()>0

	def GetSelectedItemCount(self):
		return self.hListCtrl.GetSelectedItemCount()

	def GetSelectedItems(self,index_mode=False):
		"""選択中のアイテムを、 ListObject で帰す。index_mode が true の場合、 リスト上での index のリストを返す。"""
		next=self.hListCtrl.GetFirstSelected()
		if next==-1: return None
		lst=[]
		while(True):
			if index_mode:
				lst.append(next)
			else:
				lst.append(self.listObject.GetElement(next))
			next=self.hListCtrl.GetNextSelected(next)
			if next==-1: break
		#end while
		#リストを作る
		if index_mode: return lst
		r=type(self.listObject)()
		r.Initialize(lst)
		return r
		#end GetSelectedItems

	def GetListCtrl(self):
		return self.hListCtrl

	def SetListColumns(self,lst):
		"""リストコントロールにカラムを設定する。"""
		col=lst.GetColumns()
		self.hListCtrl.DeleteAllColumns()
		i=0
		for elem,format in col.items():
			self.hListCtrl.InsertColumn(i,elem,format=format,width=wx.LIST_AUTOSIZE)
			i+=1
		#end カラムを作る
		#カラム幅を設定
		for i in range(0,len(col)):
			w=globalVars.app.config[lst.__class__.__name__]["column_width_"+str(i)]
			w=100 if w=="" else int(w)
			self.hListCtrl.SetColumnWidth(i,w)
		#end カラム幅を設定
	#end SetListColumns

	def UpdateListContent(self,content):
		"""リストコントロールの中身を更新する。カラム設定は含まない。"""
		self.log.debug("Updating list control...")
		self._cancelBackgroundTasks()
		self.ItemSelected()		#メニューバーのアイテムの状態更新処理。選択中アイテムがいったん0になってる場合があるため必要。
		t=misc.Timer()
		for elem in content:
			self.hListCtrl.Append(elem)
		#end 追加
		self.log.debug("List control updated in %f seconds." % t.elapsed)

	def MakeDirectory(self):
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

	def KeyDown(self,event):
		"""キーが押されたらここにくる。SpaceがEnterと同一視されるので対策する。"""
		if not event.GetKeyCode()==32:
			event.Skip()
		else:
			self.OnSpaceKey()

	def OnSpaceKey(self):
		"""spaceキー押下時、アイテムをチェック/チェック解除する"""
		#item=self.hListCtrl.GetItem(self.GetFocusedItem())
		if self.hListCtrl.GetItemState(self.GetFocusedItem(),wx.LIST_STATE_DROPHILITED)==wx.LIST_STATE_DROPHILITED:
			#チェック解除
			self.hListCtrl.SetItemState(self.GetFocusedItem(),0,wx.LIST_STATE_DROPHILITED)
			self.hListCtrl.SetItemState(self.GetFocusedItem(),0,wx.LIST_STATE_SELECTED)

			globalVars.app.say(_("チェック解除"))
			self.hListCtrl.Update()
		else:
			#チェック
			self.hListCtrl.SetItemState(self.GetFocusedItem(),wx.LIST_STATE_DROPHILITED, wx.LIST_STATE_DROPHILITED)
			#item.SetBackgroundColour(wx.Colour("#ff00ff"))
			#self.hListCtrl.RefreshItem(self.GetFocusedItem())
			globalVars.app.say(_("チェック"))
		#カーソルを１つ下へ移動
		self.hListCtrl.Focus(self.GetFocusedItem()+1)
		self.hListCtrl.Select(self.GetFocusedItem())

	def BeginDrag(self,event):
		data=wx.FileDataObject()
		for f in self.GetSelectedItems():
			data.AddFile(f.fullpath)

		obj=wx.DropSource(data,globalVars.app.hMainView.hFrame)
		obj.DoDragDrop()

	def SelectAll(self):
		globalVars.app.say(_("全て選択"))
		for i in range(self.hListCtrl.GetItemCount()):
			self.hListCtrl.Select(i)

	def NameCopy(self):
		if not self.IsItemSelected(): return
		globalVars.app.say(_("ファイル名をコピー"))
		t=self.GetSelectedItems().GetItemNames()
		t="\n".join(t)
		with clipboardHelper.Clipboard() as c:
			c.set_unicode_text(t)

	def FullpathCopy(self):
		if not self.IsItemSelected(): return
		t=self.GetSelectedItems().GetItemPaths()
		globalVars.app.say(_("フルパスをコピー"))
		t="\n".join(t)
		with clipboardHelper.Clipboard() as c:
			c.set_unicode_text(t)

	def UpdateFilelist(self,silence=False,cursorTargetName=""):
		"""同じリストで、内容を再取得して更新する。"""
		if silence==False:
			globalVars.app.say(_("更新"))
		if cursorTargetName=="":
			item=self.listObject.GetElement(self.GetFocusedItem())
		result=self.listObject.Update()
		if result != errorCodes.OK:
			return errorCodes.FILE_NOT_FOUND			#アクセス負荷など
		if cursorTargetName=="":
			cursor=self.listObject.Search(item.basename,0)
		else:
			cursor=self.listObject.Search(cursorTargetName,0)
		self.Update(self.listObject,cursor)

	def SortCycleAd(self):
		"""昇順と降順を交互に切り替える。"""
		self.listObject.SetSortDescending(self.listObject.GetSortDescending()==0)
		self._updateConfig()
		self.listObject.ApplySort()
		self.hListCtrl.DeleteAllItems()
		self.UpdateListContent(self.listObject.GetItems())

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
		self._updateConfig()
		self.listObject.ApplySort()
		self.hListCtrl.DeleteAllItems()
		self.UpdateListContent(self.listObject.GetItems())

	def _updateConfig(self):
		"""ソートの設定をconfigに反映する。"""
		s=self.listObject.__class__.__name__
		globalVars.app.config[s]["sorting"]=self.listObject.GetSortCursor()
		globalVars.app.config[s]["descending"]=int(self.listObject.GetSortDescending())

	def col_resize(self,event):
		no=event.GetColumn()
		width=self.hListCtrl.GetColumnWidth(no)
		globalVars.app.config[self.listObject.__class__.__name__]["column_width_"+str(no)]=str(width)

	def col_click(self,event):
		no=event.GetColumn()
		self.listObject.SetSortCursor(no)
		if self.listObject.GetSortCursor()==no:
			self.listObject.SetSortDescending(self.listObject.GetSortDescending()==0)
		self._updateConfig()
		self.listObject.ApplySort()
		self.hListCtrl.DeleteAllItems()
		self.UpdateListContent(self.listObject.GetItems())

	def SortNext(self):
		self.listObject.SetSortCursor()
		self._updateConfig()
		self.listObject.ApplySort()
		self.hListCtrl.DeleteAllItems()
		self.UpdateListContent(self.listObject.GetItems())
	#end sortNext

	def _cancelBackgroundTasks(self):
		"""フォルダ容量計算など、バックグラウンドで走っていて、ファイルリストが更新されるといらなくなるようなものをキャンセルする。"""
		for elem in self.background_tasks:
			elem.Cancel()
		#end for
		self.background_tasks=[]

	def EnterItem(self,event):
		"""forward アクションを実行する。"""
		globalVars.app.hMainView.events.GoForward()

	def Move(self,path,cursor=""):
		"""指定の場所へ移動する。"""
		r=navigator.Navigate(path,cursor,previous_tab=self,environment=self.environment)
		return errorCodes.OK if r is self else r

	def GoForward(self,stream,admin=False):
		"""選択中のフォルダやドライブに入るか、選択中のファイルを実行する。stream=True の場合、ファイルの NTFS 副ストリームを開く。"""
		index=self.GetFocusedItem()
		elem=self.listObject.GetElement(index)
		if (not stream) and type(elem)==browsableObjects.File:#このファイルを開く
			misc.RunFile(elem.fullpath,admin)
			return
		else:
			#TODO: 管理者権限が要求され、自身が管理者権限を有していないなら、別のfalconが昇格して開くように
			return self.Move(elem.fullpath)
		#end ファイルを開くか移動するか
	#end GoForward

	def GoBackward(self):
		"""内包しているフォルダ/ドライブ一覧へ移動する。"""
		if len(self.listObject.rootDirectory)<=3:		#ドライブリストへ
			target=""
			cursorTarget=self.listObject.rootDirectory[0]
		else:
			target=os.path.split(self.listObject.rootDirectory)[0]
			cursorTarget=os.path.split(self.listObject.rootDirectory)[1]
		return self.Move(target,cursorTarget)

	def MarkSet(self):
		"""現在開いている場所をマークする"""
		globalVars.app.say(_("マーク設定"))
		self.environment["markedPlace"]=self.listObject.rootDirectory
		self.log.debug("markset at \""+self.environment["markedPlace"] + "\"")

	def GoToMark(self):
		"""マークした場所へ移動する"""
		ret=self.Move(self.environment["markedPlace"])
		if ret!=errorCodes.OK:
			return ret
		globalVars.app.say(_("マーク位置へ移動"))
		return errorCodes.OK

	def StartRename(self):
		index=self.GetFocusedItem()
		self.hListCtrl.EditLabel(index)

	def OnLabelEditStart(self,evt):
		self.isRenaming=True
		self.parent.SetShortcutEnabled(False)

	def IsMarked(self):
		return self.environment["markedPlace"]!=None

	def ItemSelected(self,event=None):
		"""リストビューのアイテムの選択・選択解除の発生時に呼ばれる"""
		c=self.GetSelectedItemCount()
		if c>2:c=2
		if self.environment["selectedItemCount"]!=c:
			#print(str(self.environment["selectedItemCount"])+"=>"+str(c))
			if self.environment["selectedItemCount"]!=None:
				globalVars.app.hMainView.menu.UnBlock(self.selectItemMenuConditions[self.environment["selectedItemCount"]])
			globalVars.app.hMainView.menu.Block(self.selectItemMenuConditions[c])
			self.environment["selectedItemCount"]=c

	def OpenContextMenu(self,event):
		RegisterMenuCommand=globalVars.app.hMainView.menu.RegisterMenuCommand

		if event:
			targetPath=self.listObject.GetElement(self.hListCtrl.HitTest(event.GetPoint())[0]).fullpath
		else:
			targetPath=self.GetFocusedElement().fullpath
		#end イベントあるか
		s=misc.GetContextMenu(targetPath)
		s_json=json.loads(s)
		menus=s_json['menus']
		hMenu = wx.Menu()
		RegisterMenuCommand(hMenu,"EDIT_COPY",_("コピー"))
		RegisterMenuCommand(hMenu,"EDIT_CUT",_("切り取り"))
		RegisterMenuCommand(hMenu,"EDIT_NAMECOPY",_("名前をコピー"))
		RegisterMenuCommand(hMenu,"EDIT_FULLPATHCOPY",_("フルパスをコピー"))
		for elem in menus:
			if elem['type']=="separator": continue
			hMenu.Append(elem['id'],elem['name'])
		#end for

		self.hListCtrl.PopupMenu(hMenu)
		hMenu.Destroy()

	def CloseContextMenu(self,event):
		misc.DestroyContextMenu()
		selected=event.GetId()							#メニュー識別しの数値

		if selected>=5000:
			event.Skip()
		else:
			pass

