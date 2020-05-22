# -*- coding: utf-8 -*-
#Falcon main list tab
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
ファイルリストやドライブ一覧リストなどです。一通りのファイル操作を行うことができます。
"""

import datetime
import os
import gettext
import time
import wx
import clipboard
import errorCodes
import lists
import browsableObjects
import globalVars
import fileOperator
import misc
import views.OperationSelecter
import workerThreads
import workerThreadTasks
import fileSystemManager
import tabs.streamList
import StringUtil

from simpleDialog import *
from win32com.shell import shell, shellcon
from . import base

class FileListTab(base.FalconTabBase):
	"""ファイル/フォルダリストが表示されているタブ。"""

	blockMenuList=[
		"TOOL_EJECT_DRIVE",
		"TOOL_EJECT_DEVICE"
	]

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
		focus_index=self._findFocusAfterDeletion(paths,focus_index)
		self.Focus(focus_index)

	def Delete(self):
		focus_index=self.GetFocusedItem()
		paths=self.listObject.GetItemPaths()#パスのリストを取っておく
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
		focus_index=self._findFocusAfterDeletion(paths,focus_index)
		self.Focus(focus_index)

	def ShowProperties(self):
		index=self.GetFocusedItem()
		shell.ShellExecuteEx(shellcon.SEE_MASK_INVOKEIDLIST,0,"properties",self.listObject.GetElement(index).fullpath)

	def Copy(self):
		globalVars.app.say(_("コピー"))
		c=clipboard.ClipboardFile()
		c.SetFileList(self.GetSelectedItems().GetItemPaths())
		c.SendToClipboard()

	def Cut(self):
		globalVars.app.say(_("切り取り"))
		c=clipboard.ClipboardFile()
		c.SetOperation(clipboard.MOVE)
		c.SetFileList(self.GetSelectedItems().GetItemPaths())
		c.SendToClipboard()

	def GoToTopFile(self):
		#end ファイルリストのときしか通さない
		self.Focus(self.listObject.GetTopFileIndex())
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
		#クリップボードから情報取得し
		c=clipboard.ClipboardFile()
		target=c.GetFileList()
		if not target:
			dialog(_("エラー"),_("貼り付けるものがありません。"))
			return
		#end 貼り付ける物がない
		op=c.GetOperation()
		self.PastOperation(target,self.listObject.rootDirectory,op)

	def PastOperation(self,target,dest,op=clipboard.COPY):
		op_str=_("複写") if op==clipboard.COPY else _("移動")

		#重複を排除
		#target=set(target)

		#自身のサブフォルダへの貼り付けはできない
		errors=[]
		for i in target:
			if i in dest:
				errors.append(i)
		if errors:
			info=[
				(_("項目"),_("パス")),
				(_("%s先")%op_str,dest)
			]
			for i in errors:
				target.remove(i)
				info.append((os.path.basename(i),i))
			d=views.OperationSelecter.Dialog(_("自身のサブディレクトリへの%sはできません。")%op_str,info,views.OperationSelecter.GetMethod("OWN_SUB_DIR"),False)
			d.Initialize()
			d.Show()
			ret=d.GetValue()["response"]
			if ret=="CANCEL":return
		#TODO:同一ディレクトリなら別名を決めさせる

		#この時点でtargetが0ならおわり
		if len(target)==0:return

		#ユーザに確認表示
		if len(target)==1:
			msg=_("%(file)s\nこのファイルを、 %(dest)s に%(op)sしますか？") % {'file': target[0], 'dest': dest, 'op': op_str}
		else:
			msg=_("%(num)d 項目を、 %(dest)s に%(op)sしますか？") % {'num': len(target), 'dest': self.listObject.rootDirectory, 'op': op_str}
		#end メッセージどっちにするか
		dlg=wx.MessageDialog(None,msg,_("%(op)sの確認") % {'op': op_str}, wx.YES_NO|wx.ICON_QUESTION)
		if dlg.ShowModal()==wx.ID_NO: return

		#fileOperatorに処理依頼
		inst={"operation": "past", "target": target, "to": dest, 'copy_move_flag': op}
		op=fileOperator.FileOperator(inst)
		ret=op.Execute()

		#0.5秒待つ
		time.sleep(0.5)

		#状況確認
		#TODO:タブに分ける処理
		self.log.debug("Start checking confirmation")
		confs=op.GetConfirmationManager()
		while(True):
			confs_list=list(confs.IterateNotResponded())
			self.log.debug("%d confirmations." % len(confs_list))
			if len(confs_list)==0: break
			elem=confs_list[0]
			e=elem.GetElement()
			from_path=e.path
			dest_path=e.destpath
			from_stat=os.stat(from_path)
			dest_stat=os.stat(dest_path)
			info=[
				(_("名前"),"test.txt","",""),
				(_("サイズ"),misc.ConvertBytesTo(dest_stat.st_size,misc.UNIT_AUTO,True),"→",misc.ConvertBytesTo(from_stat.st_size,misc.UNIT_AUTO,True)),
				(_("更新日時"),datetime.datetime.fromtimestamp(dest_stat.st_mtime),"→",datetime.datetime.fromtimestamp(from_stat.st_mtime))
			]
			d=views.OperationSelecter.Dialog(_("上書きしますか？"),info,views.OperationSelecter.GetMethod("ALREADY_EXISTS"),False)
			d.Initialize()
			d.Show()
			val=d.GetValue()
			if val['all'] is True:#「以降も同様に処理」がオン
				confs.RespondAll(elem,val['response'])
			else:#この1件だけ
				elem.SetResponse(d.GetValue())#渓谷に対して、文字列でレスポンスする
			#end これ以降全てかこれだけか
		#end while
		self.log.debug("End checking confirmation.")
		op.UpdateConfirmation()#これで繁栄する
		op.Execute()#これでコピーを再実行

		if op.CheckSucceeded()==0 and ret==0:
			dialog(_("エラー"),_("%(op)sに失敗しました。" % {'op': op_str}))
		#end failure
		self.UpdateFilelist(silence=True)
	#end past


	def GetTabName(self):
		"""タブコントロールに表示する名前"""
		word=self.listObject.rootDirectory.split("\\")
		word=word[len(word)-1]
		word=StringUtil.GetLimitedString(word,globalVars.app.config["view"]["header_title_length"])
		return word
