# -*- coding: utf-8 -*-
#Filer constant values and strings
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import win32file

APP_NAME="Falcon Test"
APP_VERSION="0.01"
APP_COPYRIGHT_YEAR="2019"
APP_DEVELOPERS="Yukio Nozawa and Yuki Kochi"

SETTING_FILE_NAME="settings.ini"

APP_WINDOW_SIZE_X=1200
APP_WINDOW_SIZE_Y=800

MENUITEM_FILE_EXIT=30
MENUITEM_HELP_VERINFO=31
DRIVE_TYPE_STR={win32file.DRIVE_CDROM: "CD-ROMドライブ", win32file.DRIVE_FIXED:"ローカル ディスク", win32file.DRIVE_NO_ROOT_DIR: "ルートディレクトリなし", win32file.DRIVE_RAMDISK:"RAM ディスク", win32file.DRIVE_REMOTE:"リモート", win32file.DRIVE_REMOVABLE:"リムーバブル ディスク", win32file.DRIVE_UNKNOWN:"不明"}
