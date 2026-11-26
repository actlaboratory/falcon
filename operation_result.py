# -*- coding: utf-8 -*-
# Falcon operation result
# Note: All comments except these top lines will be written in Japanese.

"""
複数の項目を対象にするファイル操作の結果を、利用者に知らせる処理です。
すべて成功したときは件数を読み上げ、失敗した項目があるときは、その項目と理由をダイアログで表示します。
"""

from simpleDialog import dialog

import globalVars
from fileOperator import helper

# 失敗した項目を表示する最大行数
_MAX_FAILED_LINES = 10


def get_error_message(element):
    """失敗した項目(fileOperator.failedElement.FailedElement)の理由を、表示用の文章にして返す"""
    message = str(element.msg[1])
    return {
        helper.UNKNOWN_ERROR: _("処理できませんでした。"),
        helper.NO_RECYCLE_BIN: _("ゴミ箱を使えない場所のため、削除しませんでした。削除するには「完全削除」を使ってください。"),
        helper.PERMANENTLY_DELETED: _("ゴミ箱に入らず、完全に削除されました。"),
    }.get(message, message)


def report(total, succeeded, failed, success_message, failure_message):
    """
    操作の結果を知らせる。
    total は対象の数、succeeded は成功した数、failed は失敗した項目(FailedElement)のリスト。
    success_message は成功した件数 %(count)d を含む読み上げの文章。
    failure_message は成功した件数 %(succeeded)d と失敗した件数 %(failed)d を含む文章。
    """
    # 開発時は権限の昇格ができず、失敗した項目が記録されないことがあるため、件数は成功数から求める
    failed_count = max(total - succeeded, len(failed))
    if failed_count <= 0:
        globalVars.app.say(success_message % {"count": succeeded}, interrupt=True)
        return
    lines = ["%s: %s" % (element.elem, get_error_message(element).replace("\n", " ")) for element in failed[:_MAX_FAILED_LINES]]
    if len(failed) > _MAX_FAILED_LINES:
        lines.append(_("ほか %(count)d件") % {"count": len(failed) - _MAX_FAILED_LINES})
    message = failure_message % {"succeeded": succeeded, "failed": failed_count}
    if lines:
        message += "\n\n" + "\n".join(lines)
    dialog(_("エラー"), message)
