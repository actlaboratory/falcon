# -*- coding: utf-8 -*-
# Filer constant values and strings
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.

import win32file
import wx

APP_FULL_NAME = "Falcon test"
APP_NAME = "falcon"
APP_ICON = None
APP_VERSION = "0.0.1"
APP_LAST_RELEASE_DATE = "2022-01-01"
APP_COPYRIGHT_YEAR = "2019-2021"
APP_LICENSE = "Apache License 2.0"
APP_DEVELOPERS = "Yukio Nozawa, yamahubuki, ACT Laboratory"
APP_DEVELOPERS_URL = "https://actlab.org/"
APP_DETAILS_URL = "https://actlab.org/software/falcon"
APP_COPYRIGHT_MESSAGE = "Copyright (c) %s %s All lights reserved." % (APP_COPYRIGHT_YEAR, APP_DEVELOPERS)

SUPPORTING_LANGUAGE = {"ja-JP": "日本語", "en-US": "English"}  # 対応言語一覧

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

# build関連定数
BASE_PACKAGE_URL = "https://github.com/actlaboratory/falcon/releases/download/0.0.1/falcon-0.0.1.zip"
PACKAGE_CONTAIN_ITEMS = ("xd2txlib.dll", "fx")  # パッケージに含めたいファイルやfolderがあれば指定
NEED_HOOKS = ()  # pyinstallerのhookを追加したい場合は指定
STARTUP_FILE = "falcon.py"  # 起動用ファイルを指定
UPDATER_URL = "https://github.com/actlaboratory/updater/releases/download/1.0.0/updater.zip"

# update情報
UPDATE_URL = "https://actlab.org/api/checkUpdate"
UPDATER_VERSION = "1.0.0"
UPDATER_WAKE_WORD = "hello"


# menuId
MENU_ID_FROM_FALCON = 5000
MENU_ID_SORT_COLUMN = 6000

# xdoc2txtでテキスト化できる形式
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
    'po',


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
    "vbs",

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

    # JAWS for Windows configuration files
    'jbd',  # JAWS Braille Display
    'jbs',  # JAWS Braille Structure
    'jcf',  # JAWS Configuration File
    'jsi',  # JAWS Script Initialization
    'jdf',  # JAWS Dictionary File
    'jgf',  # JAWS Graphics File
    'jfd',  # JAWS Frame Definition
    'jff',  # JAWS Frame File
    'jkm',  # JAWS Key Map
    'jsd',  # JAWS Script Documentation
    'jss',  # JAWS Script Source
    'hss',  # Hidden Script Source
    'jsh',  # JAWS Script Header
    'hsh',  # Hidden Script Header
    'jsm',  # JAWS Script Message
    'his',  # History
    'qs',  # Quick Settings
    'qsm',  # quick Settings Message
    'sbl',  # Speech Symbols File
    'chr',  # Character Substitution
    'vpf',  # Voice Profile
    'jbt',  # JAWS Braille Table
    'rul',  # Research-It Rule
    'qry',  # Research-It Query
}

# xdocに書けると意図しない結果になるが、テキストとして読めるもの
TEXT_READABLE_DOCUMENT_FORMATS = {
	"xml"
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
    'wmv',
    'mpg',
    "mp4"
}

# browsableObjects.FOLDERで利用
DIR_SIZE_UNKNOWN = -1
DIR_SIZE_CALCURATING = -2
DIR_SIZE_CHECK_FAILED = -3
