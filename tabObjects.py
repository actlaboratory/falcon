# -*- coding: utf-8 -*-
#Falcon tab management
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
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
import workerThreads
import workerThreadTasks
import fileSystemManager

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
		self.task=None
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
		self.hListCtrl.Bind(wx.EVT_LIST_BEGIN_DRAG,self.BeginDrag)

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
		self._cancelBackgroundTasks()
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

	def BeginDrag(self,event):
		"""ドラッグ操作が開始された"""
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
		self.environment["FileList_descending"]=int(globalVars.app.config["FileList"]["descending"])
		self.environment["DriveList_sorting"]=int(globalVars.app.config["DriveList"]["sorting"])
		self.environment["DriveList_descending"]=int(globalVars.app.config["DriveList"]["descending"])
		self.background_tasks=[]

	def Update(self,lst,cursor=-1):
		"""指定された要素をタブに適用する。"""
		self._cancelBackgroundTasks()
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
		self.hListCtrl.Focus(cursor)
		if cursor>0:
			self.hListCtrl.Select(cursor)

	def _cancelBackgroundTasks(self):
		"""フォルダ容量計算など、バックグラウンドで走っていて、ファイルリストが更新されるといらなくなるようなものをキャンセルする。"""
		for elem in self.background_tasks:
			elem.Cancel()
		#end for
		self.background_tasks=[]

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
			if isinstance(elem,browsableObjects.Folder):#このフォルダを開く
				#TODO: 管理者モードだったら、別のfalconが昇格して開くように
				return self.move(elem.fullpath)
			#end フォルダ開く
			elif isinstance(elem,browsableObjects.File):#このファイルを開く
				if action==ACTION_FORWARD: self.RunFile(elem.fullpath,admin)
				#TODO: 管理者として副ストリーム…まぁ、使わないだろうけど一貫性のためには開くべきだと思う
				if action==ACTION_FORWARD_STREAM: self.move(elem.fullpath)
			#end ファイルを開く
			elif isinstance(elem,browsableObjects.Stream):#このストリームを開く
				self.RunFile(elem.fullpath,admin)
			#end ストリームを開く
			elif isinstance(elem,browsableObjects.Drive):#このドライブを開く
				#TODO: これも昇格したほうがいい
				self.move(elem.letter+":")
			#end ドライブ開く
			else:
				return errorCodes.NOT_SUPPORTED#そのほかはまだサポートしてない
			#end フォルダ以外のタイプ
		#end ACTION_FORWARD
		if action==ACTION_BACKWARD:
			if isinstance(self.listObject,listObjects.DriveList):
				return errorCodes.BOUNDARY
			if len(self.listObject.rootDirectory)<=3:		#ドライブリストへ
				target=""
				cursorTarget=self.listObject.rootDirectory[0]
			else:
				target=os.path.split(self.listObject.rootDirectory)[0]
				cursorTarget=os.path.split(self.listObject.rootDirectory)[1]
			return self.move(target,cursorTarget)

	def move(self,target,cursorTarget=""):
		"""targetに移動する。空文字を渡すとドライブ一覧へ"""
		targetItemIndex=-1
		target=os.path.expandvars(target)
		if target=="":#ドライブリスト
			lst=listObjects.DriveList()
			lst.Initialize(None,self.environment["DriveList_sorting"],self.environment["DriveList_descending"])
			if cursorTarget!="":
				targetItemIndex=lst.Search(cursorTarget,1)
		elif not os.path.exists(target):
			dialog(_("エラー"),_("移動に失敗しました。移動先が存在しません。"))
			return errorCodes.FILE_NOT_FOUND
		elif os.path.isfile(target):	#副ストリームへ移動
			lst=listObjects.StreamList()
			lst.Initialize(target)
		else:
			lst=listObjects.FileList()
			result=lst.Initialize(target,self.environment["FileList_sorting"],self.environment["FileList_descending"])
			if result != errorCodes.OK:
				return result#アクセス負荷
			if cursorTarget!="":
				targetItemIndex=lst.Search(cursorTarget)
		self.Update(lst)
		if targetItemIndex>=0:
			self.hListCtrl.Focus(targetItemIndex)
			self.hListCtrl.Select(targetItemIndex)
		return errorCodes.OK

	def RunFile(self,path, admin=False,prm=""):
		"""ファイルを起動する。admin=True の場合、管理者として実行する。"""
		path=os.path.expandvars(path)
		msg="running %s as admin" % (path) if admin else "running %s" % (path)
		self.log.debug(msg)
		msg=_("管理者で起動") if admin else _("起動")
		globalVars.app.say(msg)
		error=""
		if admin:
			try:
				executable=misc.GetExecutableState(path)
				p=path if executable else "cmd"
				a=prm if executable else "/c "+path+" "+prm
				ret=shell.ShellExecuteEx(shellcon.SEE_MASK_NOCLOSEPROCESS,0,"runas",p,a)
			except pywintypes.error as e:
				error=str(e)
			#end shellExecuteEx failure
		else:
			try:
				win32api.ShellExecute(0,"open",path,prm,"",1)
			except win32api.error as er:
				error=str(er)
			#end shellExecute failure
		#end admin or not
		if error!="":
			dialog(_("エラー"),_("ファイルを開くことができませんでした(%(error)s)") % {"error": error})
		#end ファイル開けなかった
	#end RunFile

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
			newName=f.directory+"\\"+e.GetLineText(0)
		else:
			newName=e.GetLineText(0)
		#end ファイルかドライブか
		if fileSystemManager.ValidationObjectName(newName):
			dialog(_("エラー"),fileSystemManager.ValidationObjectName(e.GetLineText(0)))
			evt.Veto()
			return
		inst={"operation": "rename", "files": [f.fullpath], "to": [newName]}
		op=fileOperator.FileOperator(inst)
		ret=op.Execute()
		if op.CheckSucceeded()==0:
			dialog(_("エラー"),_("名前が変更できません。"))
			evt.Veto()
			return
		#end fail
		f.basename=e.GetLineText(0)
		f.fullpath=f.directory+"\\"+f.basename
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

	def UpdateFilelist(self,silence=False,cursorTargetName=""):
		"""同じフォルダで、ファイルとフォルダ情報を最新に更新する。"""
		if silence==True:
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

	def MakeDirectory(self,newdir):
		dir=self.listObject.rootDirectory
		if fileSystemManager.ValidationObjectName(dir+"\\"+newdir):
			dialog(_("エラー"),fileSystemManager.ValidationObjectName(newdir))
			return
		dest=os.path.join(dir,newdir)
		inst={"operation": "mkdir", "target": [dest]}
		op=fileOperator.FileOperator(inst)
		ret=op.Execute()
		if op.CheckSucceeded()==0:
			dialog(_("エラー"),_("フォルダを作成できません。"))
			return
		#end error
		self.UpdateFilelist(silence=True,cursorTargetName=newdir)

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
		if self.task:
			self.task.Cancel()
		else:
			self.task=workerThreads.RegisterTask(workerThreadTasks.DebugBeep)

	def Trash(self):
		target=[]
		for elem in self.GetSelectedItems():
			target.append(elem.fullpath)
		#end for
		if len(target)==1:
			msg=_("%(file)s\nこのファイルをごみ箱に移動してもよろしいですか？") % {'file': target[0]}
		else:
			msg=_("選択中の項目 %(num)d件をごみ箱に移動してもよろしいですか？") % {'num': len(target)}
		#end メッセージどっちにするか
		dlg=wx.MessageDialog(None,msg,_("確認"),wx.YES_NO|wx.ICON_QUESTION)
		if dlg.ShowModal()==wx.ID_NO: return
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
		ret=self.move(self.markedPlace)
		if ret!=errorCodes.OK:
			return ret
		globalVars.app.say(_("マーク位置へ移動"))
		return errorCodes.OK

	def DirCalc(self):
		lst=[]
		for i in self.GetSelectedItems(index_mode=True):
			elem=self.listObject.GetElement(i)
			if elem.__class__.__name__=="Folder":
				self.hListCtrl.SetItem(index=i,column=1,label=_("<計算中>"))
				lst.append((i,elem.fullpath))
			#end フォルダだったら
		#end for
		param={'lst': lst, 'callback': self._dirCalc_receive}
		self.background_tasks.append(workerThreads.RegisterTask(workerThreadTasks.DirCalc,param))

	def _dirCalc_receive(self,results,taskState):
		"""DirCalc の結果を受ける。"""
		for elem in results:
			self.listObject.GetElement(elem[0]).size=elem[1]
			if elem[1]>=0:
				self.hListCtrl.SetItem(index=elem[0],column=1,label=misc.ConvertBytesTo(elem[1],misc.UNIT_AUTO,True))
			else:
				self.hListCtrl.SetItem(index=elem[0],column=1,label="<取得失敗>")
		#end for
		self.background_tasks.remove(taskState)

	def OnSpaceKey(self):
		"""spaceキー押下時、アイテムをチェック/チェック解除する"""
		#item=self.hListCtrl.GetItem(self.GetFocusedItem())
		#item.SetBackgroundColour(wx.Colour("#ff00ff"))
		#self.hListCtrl.RefreshItem(self.GetFocusedItem())
		if self.hListCtrl.GetItemState(self.GetFocusedItem(),wx.LIST_STATE_DROPHILITED)==wx.LIST_STATE_DROPHILITED:
			#チェック解除
			self.hListCtrl.SetItemState(self.GetFocusedItem(),0,wx.LIST_STATE_DROPHILITED)
			self.hListCtrl.SetItemState(self.GetFocusedItem(),0,wx.LIST_STATE_SELECTED)

			globalVars.app.say(_("チェック解除"))
			self.hListCtrl.Update()
		else:
			#チェック
			self.hListCtrl.SetItemState(self.GetFocusedItem(),wx.LIST_STATE_DROPHILITED, wx.LIST_STATE_DROPHILITED)
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

