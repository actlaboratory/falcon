# -*- coding: utf-8 -*-
# Falcon menu blocker
# Copyright (C) 2021 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import browsableObjects
import tabs
import menuItemsStore

# タブの種類によるブロック
tabTypeBlockList={
	tabs.driveList.DriveListTab : [
        "FILE_CHANGEATTRIBUTE",
        "FILE_TRASH",
        "FILE_DELETE",
        "FILE_MKDIR",
        "EDIT_CUT",
        "EDIT_PAST",
        "EDIT_SEARCH",
        "MOVE_BACKWARD",
        "MOVE_TOPFILE",
        "MOVE_OPEN_HERE_",
        "TOOL_DIRCALC",
        "TOOL_HASHCALC",
        "TOOL_ADDPATH",
        "TOOL_EXEC_PROGRAM",
        "READ_CONTENT_PREVIEW",
        "READ_CONTENT_READHEADER",
        "READ_CONTENT_READFOOTER",
    ],
	tabs.fileList.FileListTab : [
        "TOOL_EJECT_DRIVE",
        "TOOL_EJECT_DEVICE"
    ],
	tabs.NetworkResourceList.NetworkResourceListTab : [
        "FILE_RENAME",
        "FILE_CHANGEATTRIBUTE",
        "FILE_TRASH",
        "FILE_DELETE",
        "FILE_MKDIR",
        "EDIT_CUT",
        "EDIT_PAST",
        "EDIT_SEARCH",
        "MOVE_FORWARD_STREAM",
        "MOVE_TOPFILE",
        "MOVE_OPEN_HERE_",
        "TOOL_DIRCALC",
        "TOOL_HASHCALC",
        "TOOL_ADDPATH",
        "TOOL_EXEC_PROGRAM",
        "TOOL_EJECT_DRIVE",
        "TOOL_EJECT_DEVICE",
        "READ_CONTENT_PREVIEW",
        "READ_CONTENT_READHEADER",
        "READ_CONTENT_READFOOTER",
	],
	tabs.pastProgress.PastProgressTab : [
        "FILE_RENAME",
        "FILE_CHANGEATTRIBUTE",
        "FILE_MAKESHORTCUT",
        "FILE_TRASH",
        "FILE_DELETE",
        "FILE_MKDIR",
        "EDIT_COPY",
        "EDIT_CUT",
        "EDIT_PAST",
        "EDIT_SEARCH",
        "EDIT_UPDATEFILELIST",
        "MOVE_FORWARD",
        "MOVE_FORWARD_ADMIN",
        "MOVE_EXEC_ORIGINAL_ASSOCIATION",
        "MOVE_FORWARD_TAB",
        "MOVE_FORWARD_STREAM",
        "MOVE_BACKWARD",
        "MOVE_TOPFILE",
        "MOVE_HIST_NEXT",
        "MOVE_HIST_PREV",
        "MOVE_MARKSET",
        "MOVE_MARK",
        "READ_CONTENT_PREVIEW",
        "READ_CONTENT_READHEADER",
        "READ_CONTENT_READFOOTER",
        "TOOL_DIRCALC",
        "TOOL_HASHCALC",
        "TOOL_ADDPATH",
        "TOOL_EJECT_DRIVE",
        "TOOL_EJECT_DEVICE",
        "VIEW_DRIVE_INFO",
	],
	tabs.grepResult.GrepResultTab : [
        "MOVE_FORWARD_TAB",
        "MOVE_TOPFILE",
	],
	tabs.searchResult.SearchResultTab : [
		
	],
	tabs.streamList.StreamListTab : [
        "FILE_CHANGEATTRIBUTE",
        "FILE_MKDIR",
        "FILE_TRASH",
        "EDIT_SEARCH",
        "MOVE_FORWARD_TAB",
        "MOVE_FORWARD_STREAM",
        "MOVE_TOPFILE",
        "MOVE_OPEN_HERE_",
        "TOOL_DIRCALC",
        "TOOL_HASHCALC",
        "TOOL_ADDPATH",
        "TOOL_EJECT_DRIVE",
        "TOOL_EJECT_DEVICE",
        "TOOL_EXEC_PROGRAM",
        "READ_CONTENT_PREVIEW",
        "READ_CONTENT_READHEADER",
        "READ_CONTENT_READFOOTER",
	]
}

# 検索結果タブ共通のブロック要素を適用
for t in (tabs.searchResult.SearchResultTab,tabs.grepResult.GrepResultTab):
	tabTypeBlockList[t] += [
        "FILE_MKDIR",
        "EDIT_PAST",
        "EDIT_SEARCH",
        "MOVE_BACKWARD",
        "MOVE_HIST_PREV",
        "MOVE_HIST_NEXT",
        "MOVE_MARKSET",
        "MOVE_MARK",
        "TOOL_ADDPATH",
        "TOOL_EJECT_DRIVE",
        "TOOL_EJECT_DEVICE",
        "TOOL_EXEC_PROGRAM"
	]

# 選択中のアイテムの個数によるブロック
selectedItemCountBlockList={
	0 : [
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
	],
	1 : [
	],
	2 : [		# 2以上の場合はすべて2を適用
		"FILE_RENAME",
		"FILE_MAKESHORTCUT",
		"FILE_VIEW_DETAIL",
		"FILE_SHOWPROPERTIES",
		"EDIT_OPENCONTEXTMENU",
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
	]
}

# 選択中のアイテムの種類によるブロック
# タブのタイプによるブロックでは不足する場合にのみ利用する
selectedItemTypeBlockList={
	browsableObjects.File : [
        "TOOL_DIRCALC",
        "MOVE_FORWARD_TAB",
        "TOOL_ADDPATH",
        "MOVE_FORWARD_TAB",
        "TOOL_EJECT_DRIVE",
        "TOOL_EJECT_DEVICE",
	],
	browsableObjects.Folder : [
        "TOOL_HASHCALC",
        "READ_CONTENT_PREVIEW",
        "READ_CONTENT_READHEADER",
        "READ_CONTENT_READFOOTER",
        "TOOL_EJECT_DRIVE",
        "TOOL_EJECT_DEVICE"
	],
	browsableObjects.Drive : [
	],
	browsableObjects.NetworkResource : [
        "FILE_RENAME",
        "TOOL_EJECT_DRIVE",
        "TOOL_EJECT_DEVICE",
        "READ_CONTENT_PREVIEW"
	],
}
# 検索結果のフォルダ・ファイルは通常のファイル・フォルダと同じにする
selectedItemTypeBlockList[browsableObjects.SearchedFile] = selectedItemTypeBlockList[browsableObjects.File]
selectedItemTypeBlockList[browsableObjects.SearchedFolder] = selectedItemTypeBlockList[browsableObjects.Folder]


# 上記を基にrefName→refにして保存しておく
l1 = {}
for k,l in tabTypeBlockList.items():
	l1[k]=[]
	for r in l:
		l1[k].append(menuItemsStore.getRef(r))
l2 = {}
for k,l in selectedItemCountBlockList.items():
	l2[k]=[]
	for r in l:
		l2[k].append(menuItemsStore.getRef(r))
l3 = {}
for k,l in selectedItemTypeBlockList.items():
	l3[k]=[]
	for r in l:
		l3[k].append(menuItemsStore.getRef(r))

# 指定されたactiveTabにおいて無効なメニューの一覧を返す
def testMenu(tab):
	# 結果の格納用
	ret = set()

	# l1 タブの種類によるブロック
	try:
		ret |= set(l1[type(tab)])
	except KeyError:
		pass

	# L2/L3 に利用する情報の準備
	lst =  tab.GetSelectedItems(False)
	count = len(lst)
	if count > 2 : count = 2

	# L2 選択項目数によるブロック
	ret |= set(l2[count])

	# L3 選択中の項目の種類によるブロック
	selectedTypes = set()
	for i in lst:
		selectedTypes.add(type(i))
	for i in selectedTypes:
		try:
			ret |= set(l3[i])
		except KeyError:
			pass

	# 結果を返却
	return ret
