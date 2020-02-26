# -*- coding: utf-8 -*-
#Falcon tab creator / navigator
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
なにもない状態からパス指定でタブを作ったり、既存のタブを指定してフォルダ移動したりできます。
"""

import ctypes
import logging
import wx
import errorCodes
import lists
import globalVars
import constants
import misc
from . import fileList,driveList,streamList
from simpleDialog import dialog

	def Navigate(self,target,cursor="",previous_tab=None,main_view_handle=None):
	"""
		指定したパスにアクセスする。現在のタブと違う種類のタブが必要とされた場合に、新しいタブを返す。今のタブを再利用した場合は、Trueを返す。失敗時にはエラーコードを返す。
		パスに空の文字を指定すると、ドライブリストへ行く。
	"""
	if previous_tab is None and main_view_handle is None: return errorCodes.INVALID_PARAMETER
	parent=previous_tab.parent if previous_tab is not None else main_view_handle
	hListCtrl=previous_tab.hListCtrl if previous_tab is not None else None
	targetItemIndex=-1
	if target=="":#ドライブリスト
		if isinstance(previous_tab,driveList.DriveListTab):#再利用
			newtab=previous_tab
		else:
			newtab=driveList.DriveListTab()
			newtab.Initialize(parent,None,hListCtrl)
		#end 再利用するかどうか
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
		if isinstance(previous_tab,streamList.StreamListTab):#再利用
			newtab=previous_tab
		else:
			newtab=streamList.StreamListTab()
			newtab.Initialize(parent,None,hListCtrl)
		#end 再利用するかどうか
		newtab.Update(lst)
		return newtab
	else:
		lst=lists.FileList()
		result=lst.Initialize(FILELIST_SORTING,FILELIST_DESCENDING)
		if result != errorCodes.OK:
			if result==errorCodes.ACCESS_DENIED and not ctypes.windll.shell32.IsUserAnAdmin():
				dlg=wx.MessageDialog(None,_("アクセスが拒否されました。管理者としてFalconを別ウィンドウで立ち上げて再試行しますか？"),_("確認"),wx.YES_NO|wx.ICON_QUESTION)
				if dlg.ShowModal()==wx.ID_YES:
					misc.RunFile(sys.argv[0],True,target)
			return result#アクセス負荷
		if cursorTarget!="":
			targetItemIndex=lst.Search(cursorTarget)
		if isinstance(previous_tab,fileList.FileListTab):#再利用
			newtab=previous_tab
		else:
			newtab=fileList.FileListTab()
			newtab.Initialize(parent,None,hListCtrl)
		#end 再利用するかどうか
	newtab.Update(lst)
	if targetItemIndex>=0:
		hListCtrl.Focus(targetItemIndex)
		hListCtrl.Select(targetItemIndex)
	return newtab
#end Navigate
