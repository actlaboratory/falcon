# -*- coding: utf-8 -*-
#Falcon listObject constants
#Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

SORT_ASCENDING=False
SORT_DESCENDING=1

SORT_TYPE_BASENAME=1
SORT_TYPE_FILESIZE=2
SORT_TYPE_MODDATE=3
SORT_TYPE_ATTRIBUTES=4
SORT_TYPE_TYPESTRING=5
SORT_TYPE_VOLUMELABEL=6
SORT_TYPE_DRIVELETTER=7
SORT_TYPE_TOTALSPACE=8
SORT_TYPE_FREESPACE=9
SORT_TYPE_SEARCHPATH=9

SORT_DESCRIPTIONS=None

READONLY=0
HIDDEN=1
SYSTEM=2
ARCHIVE=3

def GetSortDescription(attrib):
	global SORT_DESCRIPTIONS
	if SORT_DESCRIPTIONS is None:
		SORT_DESCRIPTIONS={
			SORT_TYPE_BASENAME: _("ファイル名"),
			SORT_TYPE_FILESIZE: _("ファイルサイズ"),
			SORT_TYPE_MODDATE:_("更新日時"),
			SORT_TYPE_ATTRIBUTES:_("属性"),
			SORT_TYPE_TYPESTRING:_("種類"),
			SORT_TYPE_VOLUMELABEL:_("ラベル"),
			SORT_TYPE_DRIVELETTER:_("ラベル"),
			SORT_TYPE_FREESPACE:_("空き"),
			SORT_TYPE_TOTALSPACE:_("合計")
		}
	#end 辞書作る
	return SORT_DESCRIPTIONS[attrib]

