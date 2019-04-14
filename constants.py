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
DRIVE_TYPE_STR={win32file.DRIVE_CDROM: "CD-ROM�h���C�u", win32file.DRIVE_FIXED:"���[�J�� �f�B�X�N", win32file.DRIVE_NO_ROOT_DIR: "���[�g�f�B���N�g���Ȃ�", win32file.DRIVE_RAMDISK:"RAM �f�B�X�N", win32file.DRIVE_REMOTE:"�����[�g", win32file.DRIVE_REMOVABLE:"�����[�o�u�� �f�B�X�N", win32file.DRIVE_UNKNOWN:"�s��"}
