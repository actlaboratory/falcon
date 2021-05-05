# -*- coding: utf-8 -*-
# Falcon menu blocker
# Copyright (C) 2021 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import browsableObjects
import tabs
import menuItemsStore

# �^�u�̎�ނɂ��u���b�N
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

# �������ʃ^�u���ʂ̃u���b�N�v�f��K�p
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

# �I�𒆂̃A�C�e���̌��ɂ��u���b�N
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
	2 : [		# 2�ȏ�̏ꍇ�͂��ׂ�2��K�p
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

# �I�𒆂̃A�C�e���̎�ނɂ��u���b�N
# �^�u�̃^�C�v�ɂ��u���b�N�ł͕s������ꍇ�ɂ̂ݗ��p����
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
# �������ʂ̃t�H���_�E�t�@�C���͒ʏ�̃t�@�C���E�t�H���_�Ɠ����ɂ���
selectedItemTypeBlockList[browsableObjects.SearchedFile] = selectedItemTypeBlockList[browsableObjects.File]
selectedItemTypeBlockList[browsableObjects.SearchedFolder] = selectedItemTypeBlockList[browsableObjects.Folder]


# ��L�����refName��ref�ɂ��ĕۑ����Ă���
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

# �w�肳�ꂽactiveTab�ɂ����Ė����ȃ��j���[�̈ꗗ��Ԃ�
def testMenu(tab):
	# ���ʂ̊i�[�p
	ret = set()

	# l1 �^�u�̎�ނɂ��u���b�N
	try:
		ret |= set(l1[type(tab)])
	except KeyError:
		pass

	# L2/L3 �ɗ��p������̏���
	lst =  tab.GetSelectedItems(False)
	count = len(lst)
	if count > 2 : count = 2

	# L2 �I�����ڐ��ɂ��u���b�N
	ret |= set(l2[count])

	# L3 �I�𒆂̍��ڂ̎�ނɂ��u���b�N
	selectedTypes = set()
	for i in lst:
		selectedTypes.add(type(i))
	for i in selectedTypes:
		try:
			ret |= set(l3[i])
		except KeyError:
			pass

	# ���ʂ�ԋp
	return ret
