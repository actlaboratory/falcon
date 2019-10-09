# -*- coding: utf-8 -*-
#Filer constant values and strings
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import win32file
import wx

APP_NAME="Falcon Test"
APP_VERSION="0.01"
APP_COPYRIGHT_YEAR="2019"
APP_DEVELOPERS="Yukio Nozawa and Yuki Kochi"

SETTING_FILE_NAME="settings.ini"
KEYMAP_FILE_NAME="keymap.ini"

FONT_MIN_SIZE=5
FONT_MAX_SIZE=35


MENU_ITEMS={
	"FILE_RENAME": wx.NewIdRef(),
	"FILE_CHANGEATTRIBUTE": wx.NewIdRef(),
	"FILE_EXIT": wx.NewIdRef(),
	"EDIT_SORTNEXT": wx.NewIdRef(),
	"EDIT_SORTSELECT": wx.NewIdRef(),
	"EDIT_SORTCYCLEAD": wx.NewIdRef(),
	"MOVE_BACKWARD": wx.NewIdRef(),
	"MOVE_FORWARD": wx.NewIdRef(),
	"MOVE_FORWARD_ADMIN": wx.NewIdRef(),
	"MOVE_FORWARD_STREAM": wx.NewIdRef(),
	"ENV_TESTDIALOG": wx.NewIdRef(),
	"ENV_FONTTEST": wx.NewIdRef(),
	"HELP_VERINFO": wx.NewIdRef()
}
