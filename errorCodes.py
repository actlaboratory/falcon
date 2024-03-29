﻿# -*- coding: utf-8 -*-
# Falcon common error codes
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
エラーコードは、Falconの全体で共通です。ここに書かれているもの以外のエラーコードを定義してはいけません。
"""

OK = 0  # 成功(エラーなし)
NOT_SUPPORTED = 1  # サポートされていない呼び出し
BOUNDARY = 2  # 境界に到達したためリジェクト
FILE_NOT_FOUND = 3  # ファイルが存在しない
PARSING_FAILED = 4  # パーシングエラー
FATAL = 5  # 続行不可能なエラー
ACCESS_DENIED = 6  # アクセス拒否
INVALID_PARAMETER = 7  # 引数が違う
UPDATER_NEED_UPDATE = 200  # アップデートが必要
UPDATER_LATEST = 204  # アップデートが無い
UPDATER_VISIT_SITE = 205
UPDATER_BAD_PARAM = 400  # パラメーターが不正
UPDATER_NOT_FOUND = 404  # アプリケーションが存在しない


UNKNOWN = 99999
