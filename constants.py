# -*- coding: utf-8 -*-
# Filer constant values and strings
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.

import win32file
import wx

APP_NAME = "Falcon test"
APP_VERSION = "0.01"
APP_COPYRIGHT_YEAR = "2019-2020"
APP_DEVELOPERS = "Yukio Nozawa and Yuki Kochi"

SUPPORTING_LANGUAGE = {"ja-JP": "日本語", "en-US": "English"}  # 対応言語一覧
DISPLAY_LANGUAGE = ("日本語", "English")  # 言語選択表示用の文字列


SETTING_FILE_NAME = "settings.ini"
LOG_PREFIX = "falcon"
LOG_FILE_NAME = "falcon.log"
KEYMAP_FILE_NAME = "keymap.ini"
HISTORY_FILE_NAME = "history.dat"

FONT_MIN_SIZE = 5
FONT_MAX_SIZE = 35

NOT_CHECKED = wx.CHK_UNCHECKED
HALF_CHECKED = wx.CHK_UNDETERMINED
FULL_CHECKED = wx.CHK_CHECKED

ARROW_UP = 0
ARROW_RIGHT = 1
ARROW_DOWN = 2
ARROW_LEFT = 3

# menuId
MENU_ID_FROM_FALCON = 5000
MENU_ID_SORT_COLUMN = 6000

SUPPORTED_DOCUMENT_FORMATS = {
    # document
    'txt',
    'pdf',
    'rtf',
    'tex',

    # Microsoft Office
    'docx',
    'xlsx',
    'pptx',
    'doc',
    'xls',
    'ppt',

    # datafile
    'csv',
    'tsv',

    # data markup languages
    'mht',
    'htm',
    'html',
    'xml',
    'yaml',
    'md',

    #email and adressbook
    'vmg',
    'vcf',
    'eml',

    # open Office document
    'odt',  # open document
    'ods',  # open document spreadSheet
    'odp',  # open document presentation
    'odg',  # open document graphick

    # Ichitaro
    'jaw',
    'jtw',
    'jbw',
    'juw',
    'jfw',
    'jvw',
    'jtd',
    'jtt',

    # others
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
    'sxw',
    'sxc',
    'sxi',
    'sxd',


    # programing languages
    'c',
    'h',
    'cpp',
    'cs',
    'java',
    'py',
    'hsp',
    'as',
    'js',
    'rb',
    'cgi',
    'php',
    'sql',
    'manifest',

    #configuration and logs
    'ini',
    'conf',
    'url',
    'log',
    'json',
    "css",
    "htaccess",  # apache directory configuration

    # shell script
    'bat',  # windows commandPrompt
    "ps1",  # windows PowerShell
    "sh",  # Shell Script

    # git
    'gitconfig',
    'gitignore',
}

SUPPORTED_AUDIO_FORMATS = {
    'wav',
    'mp3',
    'ogg',
    'wma',
    'flac',
    'aac',
    'm4a',
    'm4r',
    "mp4"
}
# browsableObjects.FOLDERで利用
DIR_SIZE_UNKNOWN = -1
DIR_SIZE_CALCURATING = -2
DIR_SIZE_CHECK_FAILED = -3
