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

NOT_CHECKED=wx.CHK_UNCHECKED
HALF_CHECKED=wx.CHK_UNDETERMINED
FULL_CHECKED=wx.CHK_CHECKED

SUPPORTED_DOCUMENT_FORMATS={
	'txt',
	'pdf',
	'rtf',
	'docx',
	'xlsx',
	'pptx',
	'doc',
	'xls',
	'ppt',
	'mht',
	'html',
	'eml',
	'sxw',
	'sxc',
	'sxi',
	'sxd',
	'odt',
	'ods',
	'odp',
	'odg',
	'jaw',
	'jtw',
	'jbw',
	'juw',
	'jfw',
	'jvw',
	'jtd',
	'jtt',
	'oas',
	'oa2',
	'oa3',
	'bun',
	'wj2',
	'wj3',
	'wk3',
	'wk4',
	'123',
	'wri',
	'ini',
	'md',
	'py',
	'cpp',
	'hsp',
	'js',
	'rb',
	'as'
}

SUPPORTED_AUDIO_FORMATS={
	'wav',
	'mp3',
	'ogg',
	'wma',
	'flac',
	'aac',
	'm4a'
}
