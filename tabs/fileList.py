# -*- coding: utf-8 -*-
#Falcon main list tab
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
ファイルリストやドライブ一覧リストなどです。一通りのファイル操作を行うことができます。
"""

import os
import gettext
import wx
import clipboard
import errorCodes
import lists
import browsableObjects
import globalVars
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

	blockMenuList=[
		"TOOL_EJECT_DRIVE",
		"TOOL_EJECT_DEVICE"
	]

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

	def OnLabelEditEnd(self,evt):
		self.isRenaming=False
		self.parent.SetShortcutEnabled(True)
		if evt.IsEditCancelled():		#ユーザによる編集キャンセル
			return
		e=self.hListCtrl.GetEditControl()
		f=self.listObject.GetElement(self.GetFocusedItem())
		if isinstance(f,browsableObjects.Folder):
			newName=f.directory+"\\"+e.GetLineText(0)
			error=fileSystemManager.ValidationObjectName(newName,fileSystemManager.pathTypes.DIRECTORY)
		elif isinstance(f,browsableObjects.File):
			newName=f.directory+"\\"+e.GetLineText(0)
			error=fileSystemManager.ValidationObjectName(newName,fileSystemManager.pathTypes.FILE)
		#end フォルダかファイルか
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
		self.hListCtrl.Select(focus_index)

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
		#end ファイルリストのときしか通さない
		self.hListCtrl.Focus(self.listObject.GetTopFileIndex())
		self.hListCtrl.Select(-1,0)
		self.hListCtrl.Select(self.listObject.GetTopFileIndex())
		globalVars.app.say(_("先頭ファイル"))

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

	def ReadCurrentFolder(self):
		f=self.listObject.rootDirectory.split(":\\")
		s=_("現在は、ドライブ%(drive)sの %(folder)s") % {'drive': self.listObject.rootDirectory[0], 'folder': f[1] if len(f)==2 else "ルート"}
		globalVars.app.say(s, interrupt=True)

	def ReadListItemNumber(self,short=False):
		folders,files=self.listObject.GetFolderFileNumber()
		if short:
			globalVars.app.say(_("フォルダ数 %(folders)d ファイル数 %(files)d") % {'folders': folders, 'files': files})
			return
		#end short
		tmp=self.listObject.rootDirectory.split("\\")
		curdir=_("%(letter)sルート") % {'letter': tmp[0][0]} if len(tmp)==1 else tmp[-1]
		globalVars.app.say(_("%(containing)sの中には、フォルダ %(folders)d個、 ファイル %(files)d個") % {'containing': curdir, 'folders': folders, 'files': files}, interrupt=True)

	def ReadListInfo(self):
		tmp=self.listObject.rootDirectory.split("\\")
		curdir=_("%(letter)sルート") % {'letter': tmp[0][0]} if len(tmp)==1 else tmp[-1]
		prefix=_("フォルダ ") if len(tmp)>1 else ""
		globalVars.app.say(_("%(prefix)s%(dir)sを %(sortkind)sの%(sortad)sで一覧中、 %(max)d個中 %(current)d個目") %{'prefix': prefix, 'dir': curdir, 'sortkind': self.listObject.GetSortKindString(), 'sortad': self.listObject.GetSortAdString(), 'max': len(self.listObject), 'current': self.GetFocusedItem()+1}, interrupt=True)

	def Past(self):
		c=clipboard.ClipboardFile()
		target=c.GetFileList()
		if not target:
			dialog(_("エラー"),_("貼り付けるものがありません。"))
			return
		#end 貼り付ける物がない
		op=c.GetOperation()
		op_str=_("複写") if op==clipboard.COPY else _("移動")
		if len(target)==0: return
		if len(target)==1:
			msg=_("%(file)s\nこのファイルを、 %(dest)s に%(op)sしますか？") % {'file': target[0], 'dest': self.listObject.rootDirectory, 'op': op_str}
		else:
			msg=_("選択中の項目%(num)d件を、 %(dest)s に%(op)sしますか？") % {'num': len(target), 'dest': self.listObject.rootDirectory, 'op': op_str}
		#end メッセージどっちにするか
		dlg=wx.MessageDialog(None,msg,_("%(op)sの確認") % {'op': op_str}, wx.YES_NO|wx.ICON_QUESTION)
		if dlg.ShowModal()==wx.ID_NO: return
		inst={"operation": "past", "target": target, "to": self.listObject.rootDirectory, 'copy_move_flag': op}
		op=fileOperator.FileOperator(inst)
		ret=op.Execute()
		c=op.GetConfirmationCount()
		self.log.debug("%d confirmations" % c)
		confs=op.GetConfirmationManager()
		#for elem in confs.Iterate():#渓谷を1個ずつ処理できる
			#elem.SetResponse("overwrite")#渓谷に対して、文字列でレスポンスする
		#end for
		#op.UpdateConfirmation()#これで繁栄する
		#op.Execute()#これでコピーを再実行

		if op.CheckSucceeded()==0 and ret==0:
			dialog(_("エラー"),_("%(op)sに失敗しました。" % {'op': op_str}))
		#end failure
		self.UpdateFilelist(silence=True)

	#end past

