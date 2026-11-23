# -*- coding: utf-8 -*-
# Falcon startup file
# run python falcon.py to execute Falcon
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>

import os
import sys
# カレントディレクトリを設定
if hasattr(sys, "frozen"):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.abspath(os.path.dirname(__file__)))

import win32timezone  # ダミー


def _(string): pass  # dummy


# dllをカレントディレクトリから読み込むように設定
os.add_dll_directory(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import glob
import logging
import logging.handlers
import traceback

import viewkit
import wx

import constants
import falcon_settings
import globalVars

ERROR_LOG_FILE_NAME = "errorLog.txt"


def create_log_handler():
    """falconとviewkitで共有するログハンドラを作成する。"""
    for name in glob.glob("%s*" % constants.LOG_FILE_NAME):
        try:
            os.remove(name)
        except OSError:
            traceback.print_exc()
    try:
        handler = logging.handlers.RotatingFileHandler(
            constants.LOG_FILE_NAME, mode="w", encoding="UTF-8", maxBytes=2**20 * 256, backupCount=5)
    except OSError:
        traceback.print_exc()
        return None
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(name)s - %(levelname)s - %(message)s (%(asctime)s)"))
    logger = logging.getLogger(constants.LOG_PREFIX)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return handler


def create_main_window(ctx):
    """メインウィンドウを生成する。翻訳の初期化後に読み込む必要があるモジュールが多いため、ここでimportする。"""
    from views import main as main_window
    return main_window.MainWindow(ctx)


def main():
    if os.path.exists(ERROR_LOG_FILE_NAME):
        os.remove(ERROR_LOG_FILE_NAME)
    handler = create_log_handler()
    log = logging.getLogger(constants.LOG_PREFIX + ".Main")
    log.info("Starting %s %s as %s!" % (constants.APP_NAME, constants.APP_VERSION, "executable" if hasattr(sys, "frozen") else "interpreter"))

    # 旧バージョンの設定ファイル(ini)があれば、viewkitの設定ファイル(JSON)に移行する
    falcon_settings.migrate_from_ini()

    # ApplicationContext は wx.App の生成前にフォントを作るため、アサーションを無効にしておく
    wx.DisableAsserts()

    ctx = viewkit.ApplicationContext(
        application_name=constants.APP_NAME,
        application_version=constants.APP_VERSION,
        short_name=constants.LOG_PREFIX,
        supported_languages=constants.SUPPORTING_LANGUAGE,
        language="",
        setting_file_name=falcon_settings.SETTING_FILE_NAME,
        custom_setting_fields=falcon_settings.get_custom_setting_fields(),
        log_handler=handler if handler is not None else logging.NullHandler(),
    )
    import app as application
    app = application.FalconApp(ctx, create_main_window, handler)
    globalVars.app = app
    # 言語の設定はfalconの設定として保存されている
    ctx.language = app.settings.get_str("general", "language", "", constants.SUPPORTING_LANGUAGE.keys())
    app.run()


def exchandler(type, exc, tb):
    msg = traceback.format_exception(type, exc, tb)
    print("".join(msg))
    with open(ERROR_LOG_FILE_NAME, "a") as f:
        f.writelines(msg)
    if globalVars.app:
        globalVars.app.play_error_sound()


sys.excepthook = exchandler

if __name__ == "__main__":
    main()
