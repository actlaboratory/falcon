# -*- coding: utf-8 -*-
#Falcon tab management
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
タブは、必ずリストビューです。カラムの数と名前と、それに対応するリストの要素がタブを構成します。たとえば、ファイル一覧では「ファイル名」や「サイズ」などがカラムになり、その情報がリストに格納されています。ファイル操作の状況を示すタブの場合は、「進行率」や「状態」などがカラムの名前として想定されています。リスト上でエンターを押すことで、アクションを実行できます。ファイルビューではファイルやフォルダを開き、ファイル操作では問い合わせに応答することができます。
"""

import os
import views.ViewCreator
import gettext
import logging
import wx
import win32api
import clipboard
import clipboardHelper
import errorCodes
import listObjects
import browsableObjects
import globalVars
import constants
import fileOperator
import misc

from simpleDialog import *
from win32com.shell import shell, shellcon

#アクションの識別子
ACTION_FORWARD=0#ファイル/フォルダのオープン
ACTION_FORWARD_STREAM=1#ファイル/フォルダ/副ストリームのオープン
ACTION_BACKWARD=2#内包しているフォルダ/内包しているドライブ/副ストリームのクローズ
ACTION_SORTNEXT=3#次の並び順

class FalconTabBase(object):
	"""全てのタブに共通する基本クラス。"""
	def __init__(self):
		self.colums=[]#タブに表示されるカラムの一覧。外からは読み取りのみ。
		self.listObject=None#リストの中身を保持している listObjects のうちのどれかのオブジェクト・インスタンス
		self.type=None
		self.isRenaming=False
		globalVars.app.config.add_section(self.__class__.__name__)
		self.environment={}		#このタブ特有の環境変数
		self.markedPlace=None	#マークフォルダ

	def InstallListCtrl(self,parent):
		"""指定された親パネルの子供として、このタブ専用のリストコントロールを生成する。"""
		self.creator=views.ViewCreator.ViewCreator(1,parent)
		self.hListCtrl=self.creator.ListCtrl(1,wx.EXPAND,style=wx.LC_REPORT|wx.LC_EDIT_LABELS)
		self.hListCtrl.Bind(wx.EVT_LIST_COL_CLICK,self.col_click)
		self.hListCtrl.Bind(wx.EVT_LIST_COL_END_DRAG,self.col_resize)
		self.hListCtrl.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT,self.OnLabelEditStart)
		self.hListCtrl.Bind(wx.EVT_LIST_END_LABEL_EDIT,self.OnLabelEditEnd)
		self.hListCtrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED,self.EnterItem)
		self.hListCtrl.Bind(wx.EVT_KEY_DOWN,self.KeyDown)

	def GetListColumns(self):
		return self.columns

	def GetItems(self):
		"""タブのリストの中身を取得する。"""
		return self.listObject.GetItems() if self.listObject is not None else []

	def GetFocusedItem(self):
		"""現在フォーカスが当たっているアイテムのインデックス番号を取得する。"""
		return self.hListCtrl.GetFocusedItem()

	# 選択されているアイテムが１つ以上存在するか否か
	def IsItemSelected(self):
		return self.hListCtrl.GetSelectedItemCount()>0

	def GetSelectedItemCount(self):
		return self.hListCtrl.GetSelectedItemCount()

	def GetSelectedItems(self):
		"""選択中のアイテムを、 List オブジェクトで帰す。"""
		next=self.hListCtrl.GetFirstSelected()
		if next==-1: return None
		lst=[]
		while(True):
			lst.append(self.listObject.GetElement(next))
			next=self.hListCtrl.GetNextSelected(next)
			if next==-1: break
		#end while
		#リストを作る
		r=type(self.listObject)()
		r.Initialize(lst)
		return r
		#end GetSelectedItems

	def GetListCtrl(self):
		return self.hListCtrl

	def SetListColumns(self,col):
		"""リストコントロールにカラムを設定する。"""
		self.hListCtrl.DeleteAllColumns()
		i=0
		for elem,format in col.items():
			self.hListCtrl.InsertColumn(i,elem,format=format,width=wx.LIST_AUTOSIZE)
			i+=1

	def UpdateListContent(self,content):
		"""リストコントロールの中身を更新する。カラム設定は含まない。"""
		self.log.debug("Updating list control...")
		t=misc.Timer()
		for elem in content:
			self.hListCtrl.Append(elem)
		#end 追加
		self.log.debug("List control updated in %f seconds." % t.elapsed)

	def TriggerAction(self, action,admin=False):
		"""タブの指定要素に対してアクションを実行する。成功した場合は、errorCodes.OK を返し、失敗した場合は、その他のエラーコードを返す。admin=True で、管理者として実行する。"""
		return errorCodes.NOT_SUPPORTED#基底クラスではなにも許可しない

	def EnterItem(self,event):
		"""アイテムの上でエンターを押したときに実行される。本当はビューのショートカットキーにしたかったんだけど、エンターの入力だけはこっちでとらないとできなかった。"""
		return errorCodes.NOT_SUPPORTED#オーバーライドしてね

	def MarkSet():
		"""現在開いている場所をマークする"""
		return errorCodes.NOT_SUPPORTED#オーバーライドしてね

	def KeyDown(self,event):
		"""キーが押されたらここにくる。SpaceがEnterと同一視されるので対策する。"""
		if not event.GetKeyCode()==32:
			event.Skip()
		else:
			self.OnSpaceKey()

	def OnSpaceKey(self):
		"""Spaceキーが押されたらこれが呼ばれる。"""
		return errorCodes.NOT_SUPPORTED#オーバーライドしてね

class MainListTab(FalconTabBase):
	"""ファイル/フォルダ/ドライブリストが表示されているタブ。"""
	def Initialize(self,parent):
		"""タブを初期化する。親ウィンドウの上にリストビューを作るだけ。"""
		self.log=logging.getLogger("falcon.mainListTab")
		self.log.debug("Created.")
		self.parent=parent
		self.InstallListCtrl(parent.hListPanel)
		self.environment["FileList_sorting"]=int(globalVars.app.config["FileList"]["sorting"])
		self.environment["FileList_descending"]=int(globalVars.app.config["FileList"]["sorting"])
		self.environment["DriveList_sorting"]=int(globalVars.app.config["DriveList"]["sorting"])
		self.environment["DriveList_descending"]=int(globalVars.app.config["DriveList"]["descending"])

	def Update(self,lst):
		"""指定された要素をタブに適用する。"""
		self.hListCtrl.DeleteAllItems()
		if type(self.listObject)!=type(lst):
			self.columns=lst.GetColumns()
			self.SetListColumns(self.columns)
			for i in range(0,len(self.columns)):
				w=globalVars.app.config[lst.__class__.__name__]["column_width_"+str(i)]
				w=100 if w=="" else int(w)
				self.hListCtrl.SetColumnWidth(i,w)
		#end 違う種類のリストかどうか
		self.listObject=lst
		self.UpdateListContent(self.listObject.GetItems())

	def TriggerAction(self, action,admin=False):
		if action==ACTION_SORTNEXT:
			self.listObject.SetSortCursor()
			self._updateEnv()
			self.listObject.ApplySort()
			self.hListCtrl.DeleteAllItems()
			self.UpdateListContent(self.listObject.GetItems())
			return
		#end sortNext
		index=self.GetFocusedItem()
		if action==ACTION_FORWARD or action==ACTION_FORWARD_STREAM:
			elem=self.listObject.GetElement(index)
			self.lastBasename=elem.basename#あとでバックスペースで戻ったときに使う
			if isinstance(elem,browsableObjects.Folder):#このフォルダを開く
				#TODO: 管理者モードだったら、別のfalconが昇格して開くように
				lst=listObjects.FileList()
				ok=lst.Initialize(elem.fullpath,self.environment["FileList_sorting"],self.environment["FileList_descending"])
				if not ok: return#アクセス負荷
				self.Update(lst)
				return errorCodes.OK
			#end フォルダ開く
			elif isinstance(elem,browsableObjects.File):#このファイルを開く
				if action==ACTION_FORWARD: self.RunFile(elem,admin)
				#TODO: 管理者として副ストリーム…まぁ、使わないだろうけど一貫性のためには開くべきだと思う
				if action==ACTION_FORWARD_STREAM: self.OpenStream(elem)
			#ファイルを開く
			elif isinstance(elem,browsableObjects.Stream):#このストリームを開く
				self.RunFile(elem,admin)
			#end ストリームを開く
			elif isinstance(elem,browsableObjects.Drive):#このドライブを開く
				#TODO: これも昇格したほうがいい
				lst=listObjects.FileList()
				if not lst.Initialize(elem.letter+":",self.environment["FileList_sorting"],self.environment["FileList_descending"]):
					return errorCodes.FILE_NOT_FOUND
				self.Update(lst)
				return errorCodes.OK
			#end ドライブ開く
			else:
				return errorCodes.NOT_SUPPORTED#そのほかはまだサポートしてない
			#end フォルダ以外のタイプ
		#end ACTION_FORWARD
		if action==ACTION_BACKWARD:
			if (self.listObject.__class__.__name__=="DriveList"):
				return errorCodes.BOUNDARY
			dir=self.listObject.rootDirectory
			if len(dir)<=3:#ドライブリスト
				lst=listObjects.DriveList()
				lst.Initialize(None,self.environment["DriveList_sorting"],self.environment["DriveList_descending"])
				self.Update(lst)
				return
			#end ドライブ一覧表示
			predir=os.path.split(self.listObject.rootDirectory)[0]
			lst=listObjects.FileList()
			ok=lst.Initialize(predir,self.environment["FileList_sorting"],self.environment["FileList_descending"])
			if not ok: return#アクセス負荷
			self.Update(lst)
			self.hListCtrl.Focus(self.hListCtrl.FindItem(-1,self.lastBasename))

	def RunFile(self,elem, admin=False):
		"""ファイルを起動する。admin=True の場合、管理者として実行する。"""
		msg="running %s as admin" % (elem.fullpath) if admin else "running %s" % (elem.fullpath)
		self.log.debug(msg)
		msg=_("管理者で起動") if admin else _("起動")
		globalVars.app.say(msg)
		error=""
		if admin:
			try:
				ret=shell.ShellExecuteEx(shellcon.SEE_MASK_NOCLOSEPROCESS,0,"runas",elem.fullpath,"")
			except pywintypes.error as e:
				error=str(e)
			#end shellExecuteEx failure
		else:
			try:
				win32api.ShellExecute(0,"open",elem.fullpath,"","",1)
			except win32api.error as er:
				error=str(er)
			#end shellExecute failure
		#end admin or not
		if error!="":
			dialog(_("エラー"),_("ファイルを開くことができませんでした(%(error)s)") % {"error": error})
		#end ファイル開けなかった
	#end RunFile

	def OpenStream(self,elem):
		"""副ストリームリストを開く。"""
		lst=listObjects.StreamList()
		lst.Initialize(elem.fullpath)
		self.Update(lst)
	#end OpenStream


	def col_click(self,event):
		no=event.GetColumn()
		self.listObject.SetSortCursor(no)
		if self.listObject.GetSortCursor()==no:
			self.listObject.SetSortDescending(self.listObject.GetSortDescending()==0)
		self._updateEnv()
		self.listObject.ApplySort()
		self.hListCtrl.DeleteAllItems()
		self.UpdateListContent(self.listObject.GetItems())

	def _updateEnv(self):
		"""ソートの環境変数を更新する。"""
		s=self.listObject.__class__.__name__
		globalVars.app.config[s]["sorting"]=self.listObject.GetSortCursor()
		globalVars.app.config[s]["descending"]=int(self.listObject.GetSortDescending())
		self.environment[s+"_sorting"]=self.listObject.GetSortCursor()
		self.environment[s+"_descending"]=self.listObject.GetSortDescending()

	def col_resize(self,event):
		no=event.GetColumn()
		width=self.hListCtrl.GetColumnWidth(no)
		globalVars.app.config[self.listObject.__class__.__name__]["column_width_"+str(no)]=str(width)

	def OnLabelEditStart(self,evt):
		self.isRenaming=True
		self.parent.SetShortcutEnabled(False)

	def OnLabelEditEnd(self,evt):
		self.isRenaming=False
		self.parent.SetShortcutEnabled(True)
		if evt.IsEditCancelled():		#ユーザによる編集キャンセル
			return
		e=self.hListCtrl.GetEditControl()
		f=self.listObject.GetElement(self.hListCtrl.GetFocusedItem())
		if isinstance(f,browsableObjects.File):
			inst={"operation": "rename", "files": [f.fullpath], "to": [f.directory+"\\"+e.GetLineText(0)]}
		else:
			inst={"operation": "rename", "files": [f.fullpath], "to": [e.GetLineText(0)]}
		#end ファイルかドライブか
		op=fileOperator.FileOperator(inst)
		ret=op.Execute()
		if op.CheckSucceeded()==0:
			dialog(_("エラー"),_("名前が変更できません。"))
			evt.Veto()
		#end fail
	#end onLabelEditEnd

	def ChangeAttribute(self,attrib_checks):
		lst=self.GetSelectedItems()
		inst={"operation": "changeAttribute"}
		f=[]
		t=[]
		for elem in lst:
			attrib=elem.GetNewAttributes(attrib_checks)
			if attrib!=-1:#変更の必要があるので追加
				f.append(elem.fullpath)
				t.append(attrib)
			#end 追加
		#end 選択中のファイルの数だけ
		inst['from']=f
		inst['to_attrib']=t#to じゃないのは、日時変更に対応していたときのなごり
		op=fileOperator.FileOperator(inst)
		if len(t)==0:
			dialog(_("情報"),_("変更が必要な俗世はありませんでした。"))
			return
		#end なにも変更しなくてよかった
		ret=op.Execute()
		if op.CheckSucceeded()==0:
			dialog(_("エラー"),_("属性が変更できません。"))

	def EnterItem(self,event):
		"""forward アクションを実行する。"""
		self.TriggerAction(ACTION_FORWARD)

	def StartRename(self):
		"""リネームを開始する。"""
		index=self.GetFocusedItem()
		self.hListCtrl.EditLabel(index)

	def SortSelect(self):
		"""並び順を指定する。"""
		m=wx.Menu()
		s=self.listObject.GetSupportedSorts()
		i=0
		for elem in s:
			m.Append(i,listObjects.GetSortDescription(elem))
			i+=1
		#end 追加
		item=self.hListCtrl.GetPopupMenuSelectionFromUser(m)
		m.Destroy()
		self.listObject.SetSortCursor(item)
		self._updateEnv()
		self.listObject.ApplySort()
		self.hListCtrl.DeleteAllItems()
		self.UpdateListContent(self.listObject.GetItems())

	def SortCycleAd(self):
		"""昇順と降順を交互に切り替える。"""
		self.listObject.SetSortDescending(self.listObject.GetSortDescending()==0)
		self._updateEnv()
		self.listObject.ApplySort()
		self.hListCtrl.DeleteAllItems()
		self.UpdateListContent(self.listObject.GetItems())

	def UpdateFilelist(self,silence=False):
		"""同じフォルダで、ファイルとフォルダ情報を最新に更新する。"""
		globalVars.app.say(_("更新"))
		lst=listObjects.FileList()
		ok=lst.Initialize(self.listObject.rootDirectory)
		if not ok: return#アクセス負荷
		self.Update(lst)

	def MakeDirectory(self,newdir):
		dir=self.listObject.rootDirectory
		dest=os.path.join(dir,newdir)
		inst={"operation": "mkdir", "target": [dest]}
		op=fileOperator.FileOperator(inst)
		ret=op.Execute()
		if op.CheckSucceeded()==0:
			dialog(_("エラー"),_("フォルダを作成できません。"))
			return
		#end error
		self.UpdateFilelist(silence=True)

	def MakeShortcut(self,option):
		prm=""
		dir=""
		if option["type"]=="shortcut":
			prm=option["parameter"]
			dir=option["directory"]
		target=self.parent.activeTab.GetSelectedItems().GetElement(0).fullpath
		dest=option["destination"]
		if not os.path.isabs(dest):	#早退の場合は絶対に直す
			dest=os.path.normpath(os.path.join(os.path.dirname(target),dest))

		#TODO:
		#相対パスでの作成に後日対応する必要がある
		#ハードリンクはドライブをまたげないのでバリデーションする
		#ファイルシステムを確認し、対応してない種類のものは作れないようにバリデーションする
		#作業フォルダの指定に対応する(ファイルオペレータ側の修正も必用)

		if option["type"]=="shortcut":
			inst={"operation":option["type"], "target": [(dest,target,prm)]}
		else:
			inst={"operation":option["type"], "from": [target], "to": [dest]}
		#end ショートカットかそれ以外
		op=fileOperator.FileOperator(inst)
		ret=op.Execute()
		if op.CheckSucceeded()==0:
			dialog(_("エラー"),_("ショートカットの作成に失敗しました。"))
			return
		#end error
		self.UpdateFilelist(silence=True)

	def FileOperationTest(self):
		inst={"operation": "hardLink", "to": [os.path.abspath("help_hard.chm")], "from": [os.path.abspath("PyWin32.chm")]}
		op=fileOperator.FileOperator(inst)
		ret=op.Execute()
		if op.CheckSucceeded()==0:
			dialog(_("エラー"),_("ショートカットを作成できません。"))
			return
		#end error
		self.UpdateFilelist(silence=True)
		dialog("とりあえずテストでハードリンク作った","GUIつくってね")

	def Trash(self):
		target=[]
		for elem in self.GetSelectedItems():
			target.append(elem.fullpath)
		#end for
		inst={"operation": "trash", "target": target}
		op=fileOperator.FileOperator(inst)
		ret=op.Execute()
		if op.CheckSucceeded()==0:
			dialog(_("エラー"),_("ファイルをゴミ箱に移動できませんでした。"))
			return
		#end error
		self.UpdateFilelist(silence=True)

	def Delete(self):
		target=[]
		for elem in self.GetSelectedItems():
			target.append(elem.fullpath)
		#end for
		if len(target)==1:
			msg=_("%(file)s\nこのファイルを完全削除してもよろしいですか？") % {'file': target[0]}
		else:
			msg=_("選択中の項目 %(num)d件を完全削除してもよろしいですか？") % {'num': len(target)}
		#end メッセージどっちにするか
		dlg=wx.MessageDialog(None,msg,_("完全削除の確認"),wx.YES_NO|wx.ICON_QUESTION)
		if dlg.ShowModal()==wx.ID_NO: return
		inst={"operation": "delete", "target": target}
		op=fileOperator.FileOperator(inst)
		ret=op.Execute()
		if op.CheckSucceeded()==0:
			dialog(_("エラー"),_("削除に失敗しました。"))
			return
		#end error
		self.UpdateFilelist(silence=True)

	def ShowProperties(self):
		index=self.GetFocusedItem()
		shell.ShellExecuteEx(shellcon.SEE_MASK_INVOKEIDLIST,0,"properties",self.listObject.GetElement(index).fullpath)

	def Copy(self):
		if not self.IsItemSelected(): return
		globalVars.app.say(_("コピー"))
		c=clipboard.ClipboardFile()
		c.SetFileList(self.GetSelectedItems().GetItemPaths())
		c.SendToClipboard()

	def Cut(self):
		if not self.IsItemSelected(): return
		globalVars.app.say(_("切り取り"))
		c=clipboard.ClipboardFile()
		c.SetOperation(clipboard.MOVE)
		c.SetFileList(self.GetSelectedItems().GetItemPaths())
		c.SendToClipboard()

	def FullpathCopy(self):
		if not self.IsItemSelected(): return
		t=self.GetSelectedItems().GetItemPaths()
		globalVars.app.say(_("フルパスをコピー"))
		t="\n".join(t)
		with clipboardHelper.Clipboard() as c:
			c.set_unicode_text(t)

	def NameCopy(self):
		if not self.IsItemSelected(): return
		globalVars.app.say(_("ファイル名をコピー"))
		t=self.GetSelectedItems().GetItemNames()
		t="\n".join(t)
		with clipboardHelper.Clipboard() as c:
			c.set_unicode_text(t)

	def SelectAll(self):
		globalVars.app.say(_("全て選択"))
		for i in range(self.hListCtrl.GetItemCount()):
			self.hListCtrl.Select(i)

	def GoToTopFile(self):
		if not isinstance(self.listObject,listObjects.FileList):
			dialog(_("エラー"),_("ここではこの機能を利用できません。"))
			return
		#end ファイルリストのときしか通さない
		self.hListCtrl.Focus(self.listObject.GetTopFileIndex())
		globalVars.app.say(_("先頭ファイル"))

	def MarkSet(self):
		"""現在開いている場所をマークする"""
		globalVars.app.say(_("マーク設定"))
		self.markedPlace=self.listObject.rootDirectory
		self.log.debug("markset at \""+self.markedPlace + "\"")

	def GoToMark(self):
		if self.markedPlace=="":				#ドライブリストへ移動
			lst=listObjects.DriveList()
			lst.Initialize(None,self.environment["DriveList_sorting"],self.environment["DriveList_descending"])
		elif not os.path.exists(self.markedPlace):
			dialog(_("エラー"),_("マーク位置への移動に失敗しました。移動先が存在しません。"))
			return FILE_NOT_FOUND
		elif os.path.isfile(self.markedPlace):	#副ストリームへ移動
			lst=listObjects.StreamList()
			lst.Initialize(self.markedPlace)
		else:									#ファイルリストへ移動
			lst=listObjects.FileList()
			ok=lst.Initialize(self.markedPlace,self.environment["FileList_sorting"],self.environment["FileList_descending"])
			if not ok: return#アクセス負荷
		self.Update(lst)
		globalVars.app.say(_("マーク位置へ移動"))
		return errorCodes.OK

