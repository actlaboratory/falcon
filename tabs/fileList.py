# -*- coding: utf-8 -*-
#Falcon main list tab
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
ファイルリストやドライブ一覧リストなどです。一通りのファイル操作を行うことができます。
"""

import sys
import os
import views.ViewCreator
import gettext
import logging
import wx
import win32api
import clipboard
import clipboardHelper
import errorCodes
import lists
import browsableObjects
import globalVars
import constants
import fileOperator
import misc
import workerThreads
import workerThreadTasks
import fileSystemManager
import tabs.driveList
import tabs.streamList

from simpleDialog import *
from win32com.shell import shell, shellcon
from . import base

class FileListTab(base.FalconTabBase):
	"""ファイル/フォルダリストが表示されているタブ。"""

	def Update(self,lst,cursor=-1):
		"""指定された要素をタブに適用する。"""
		self._cancelBackgroundTasks()
		self.hListCtrl.DeleteAllItems()
		self.SetListColumns(lst)
		self.listObject=lst
		self.UpdateListContent(self.listObject.GetItems())
		self.hListCtrl.Focus(cursor)
		if cursor>0:
			self.hListCtrl.Select(cursor)
	def GoForward(self,stream,admin=False):
		"""選択中のフォルダに入るか、選択中のファイルを実行する。stream=True の場合、ファイルの NTFS 副ストリームを開く。"""
		index=self.GetFocusedItem()
		elem=self.listObject.GetElement(index)
		if isinstance(elem,browsableObjects.Folder):#このフォルダを開く
			#TODO: 管理者モードだったら、別のfalconが昇格して開くように
			return self.move(elem.fullpath)
		#end フォルダ開く
		elif isinstance(elem,browsableObjects.File):#このファイルを開く
			if not stream: misc.RunFile(elem.fullpath,admin)
			#TODO: 管理者として副ストリーム…まぁ、使わないだろうけど一貫性のためには開くべきだと思う
			if stream: return self.move(elem.fullpath)
		#end ファイルを開く
		else:
			return errorCodes.NOT_SUPPORTED#そのほかはまだサポートしてない
		#end サポートしてないタイプ
	#end GoForward

	def GoBackward(self):
		"""内包しているフォルダ/ドライブ一覧へ移動する。"""
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
		if target=="":#ドライブリスト
			newtab=tabs.driveList.DriveListTab()
			newtab.Initialize(self.parent,None,self.hListCtrl)
			newtab.Update(cursorTarget)
			return newtab
		#end ドライブリストへ行く
		target=os.path.expandvars(target)
		if not os.path.exists(target):
			dialog(_("エラー"),_("移動に失敗しました。移動先が存在しません。"))
			return errorCodes.FILE_NOT_FOUND
		elif os.path.isfile(target):	#副ストリームへ移動
			lst=lists.StreamList()
			lst.Initialize(target)
			newtab=tabs.streamList.StreamListTab()
			newtab.Initialize(self.parent,None,self.hListCtrl)
			newtab.Update(lst)
			return newtab
		else:
			lst=lists.FileList()
			result=lst.Initialize(target,self.environment["FileList_sorting"],self.environment["FileList_descending"])
			if result != errorCodes.OK:
				if result==errorCodes.ACCESS_DENIED and not ctypes.windll.shell32.IsUserAnAdmin():
					dlg=wx.MessageDialog(None,_("アクセスが拒否されました。管理者としてFalconを別ウィンドウで立ち上げて再試行しますか？"),_("確認"),wx.YES_NO|wx.ICON_QUESTION)
					if dlg.ShowModal()==wx.ID_YES:
						misc.RunFile(sys.argv[0],True,target)
				return result#アクセス負荷
			if cursorTarget!="":
				targetItemIndex=lst.Search(cursorTarget)
		self.Update(lst)
		if targetItemIndex>=0:
			self.hListCtrl.Focus(targetItemIndex)
			self.hListCtrl.Select(targetItemIndex)
		return errorCodes.OK

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
		if isinstance(f,browsableObjects.Folder):
			newName=f.directory+"\\"+e.GetLineText(0)
			error=fileSystemManager.ValidationObjectName(newName,fileSystemManager.pathTypes.DIRECTORY)
		elif isinstance(f,browsableObjects.File):
			newName=f.directory+"\\"+e.GetLineText(0)
			error=fileSystemManager.ValidationObjectName(newName,fileSystemManager.pathTypes.FILE)
		else:
			newName=e.GetLineText(0)
			error=fileSystemManager.ValidationObjectName(newName,fileSystemManager.pathTypes.VOLUME_LABEL)
		#end フォルダかファイルかドライブか
		if error:
			dialog(_("エラー"),error)
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
		if isinstance(f,browsableObjects.File):
			f.fullpath=f.directory+"\\"+f.basename
		if isinstance(f,browsableObjects.Stream):
			f.fullpath=f.file+f.basename
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

	def StartRename(self):
		"""リネームを開始する。"""
		index=self.GetFocusedItem()
		self.hListCtrl.EditLabel(index)

	def MakeDirectory(self,newdir):
		dir=self.listObject.rootDirectory
		if fileSystemManager.ValidationObjectName(dir+"\\"+newdir,fileSystemManager.pathTypes.DIRECTORY):
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
		focus_index=self.GetFocusedItem()
		paths=self.listObject.GetItemPaths()#パスのリストを取っておく
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
		failed=op.CheckFailed()
		print("fail %d" % len(failed))
		self.UpdateFilelist(silence=True)
		#カーソルをどこに動かすかを決定、まずはもともとフォーカスしてた項目があるかどうか
		if os.path.exists(paths[focus_index]):
			new_cursor_path=paths[focus_index]#フォーカスしてたファイル
		else:#あるファイルを上下に探索
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
				if tmp>=ln and os.path.exists(paths[tmp]):#あった
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
		self.hListCtrl.Focus(focus_index)

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

	def GoToTopFile(self):
		if not isinstance(self.listObject,lists.FileList):
			dialog(_("エラー"),_("ここではこの機能を利用できません。"))
			return
		#end ファイルリストのときしか通さない
		self.hListCtrl.Focus(self.listObject.GetTopFileIndex())
		self.hListCtrl.Select(-1,0)
		self.hListCtrl.Select(self.listObject.GetTopFileIndex())
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

