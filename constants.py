# -*- coding: utf-8 -*-
#Filer constant values and strings
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import win32file
import wx

APP_NAME="Falcon Test"
APP_VERSION="0.01"
APP_COPYRIGHT_YEAR="2019-2020"
APP_DEVELOPERS="Yukio Nozawa and Yuki Kochi"

SUPPORTING_LANGUAGE=("ja-JP","en-US")


SETTING_FILE_NAME="settings.ini"
KEYMAP_FILE_NAME="keymap.ini"

FONT_MIN_SIZE=5
FONT_MAX_SIZE=35

NOT_CHECKED=wx.CHK_UNCHECKED
HALF_CHECKED=wx.CHK_UNDETERMINED
FULL_CHECKED=wx.CHK_CHECKED


#menuId
MENU_ID_FROM_FALCON=5000
MENU_ID_SORT_COLUMN=6000

SUPPORTED_DOCUMENT_FORMATS={
	'txt',
	'pdf',
	'rtf',
	'docx',
	'csv',
	'tsv',
	'xlsx',
	'pptx',
	'doc',
	'xls',
	'ppt',
	'url',
	'mht',
	'htm',
	'html',
	'xml',
	'yaml',
	'json',
	'vmg',
	'vcf',
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
	'conf',
	'md',
	'py',
	'c',
	'h',
	'cpp',
	'cs',
	'java',
	'hsp',
	'js',
	'rb',
	'sql',
	'as',
	'manifest',
	'tex',
	'log',
	'bat',
	'gitconfig',
	'gitignore',
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
