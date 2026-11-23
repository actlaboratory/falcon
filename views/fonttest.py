# -*- coding: utf-8 -*-
# Falcon wx font test
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.

"""フォント設定ダイアログの動作を確認するためのテスト機能"""

from simpleDialog import dialog
from views.fontManager import FontManager


def show_font_test(parent):
    """フォント設定ダイアログを表示し、選ばれたフォントの情報を表示して設定に保存する"""
    manager = FontManager()
    if not manager.show_setting_dialog(parent):
        return False
    dialog("test", str(manager.getSize()))
    dialog("test", manager.getName())
    return True
