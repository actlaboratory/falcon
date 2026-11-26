# -*- coding: utf-8 -*-
# Falcon external file operator
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.
"""
管理者権限で起動された falcon が、アクセス拒否になったファイル操作をやり直す。

falcon 本体は、昇格が必要になると自分自身を「falcon.exe --fileop <パイプの識別子> <指示のハッシュ>」として
管理者権限で起動する（開発時は「python falcon.py --fileop ...」）。ウィンドウは出さず、本体から名前付きパイプで
受け取った操作を実行して、結果を返す。受け渡しの仕組みと安全のための確認は fileOperator/elevation.py にある。
"""
import gettext
import json
import logging
import sys

import constants
import falcon_settings

# 管理者権限で起動するときに付ける引数。fileOperator.elevation.ARGUMENT と同じ
ARGUMENT = "--fileop"

log = logging.getLogger(constants.LOG_PREFIX)


def run(pipe_id, digest):
    """本体から操作を受け取り、昇格した状態で実行する。"""
    # falcon.py の例外処理は errorLog.txt に書き込むので、管理者権限では使わない
    sys.excepthook = _on_error
    # ログはファイルに書かず、本体に返して記録してもらう（elevation.serve が集める）
    log.setLevel(logging.DEBUG)
    _install_translation()
    # 翻訳を有効にした後で読み込む
    from fileOperator import elevation
    log.info("Starting Falcon external file operation.")
    try:
        elevation.serve(pipe_id, digest, _execute)
    except elevation.ProtocolError as e:
        # 本体につなげない場合は、結果を返す先がない
        log.error("Cannot communicate with Falcon: %s" % e)
    sys.exit(0)


def _execute(instructions):
    """指示を実行し、結果を返す。"""
    import fileOperator
    operator = fileOperator.FileOperator(instructions, elevated=True)
    operator.Execute()
    log.info("End")
    return operator.output


def _on_error(exc_type, exc, tb):
    """予期しない例外では、何も書き込まずに終了する。本体には、結果が返らなかったことで失敗が伝わる。"""
    sys.exit(1)


def _install_translation():
    """本体と同じ言語で、失敗の理由などを返せるようにする。設定ファイルは読むだけで、書き込まない。"""
    language = ""
    try:
        with open(falcon_settings.SETTING_FILE_NAME, encoding="utf-8") as f:
            data = json.load(f)
        language = data["custom"][falcon_settings.CUSTOM_FIELD_NAME]["general"]["language"]
    except (OSError, ValueError, KeyError, TypeError):
        log.warning("Cannot read language setting.")
    if not isinstance(language, str) or language not in constants.SUPPORTING_LANGUAGE:
        language = ""
    gettext.translation("messages", "locale", languages=[language] if language else None, fallback=True).install()
