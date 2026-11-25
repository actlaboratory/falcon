# -*- coding: utf-8 -*-
# Falcon file operation handler trash
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.
import logging

from . import helper, recycle

VERB = "trash"
log = logging.getLogger("falcon.%s" % VERB)


def Execute(op):
    """実行処理。リトライが必要になった項目数を返す。"""
    retry = 0
    try:
        f = op.instructions["target"]
    except KeyError:
        log.error("Required key is not specified.")
        return False
    # end ゴミ箱に入れるファイルリストがない
    op.output["all_OK"] = True
    op.output["retry"]["target"] = []
    op.output["percentage"] = 0
    # シェルは1つの項目の途中経過を知らせないので、割合の反映は項目ごとになる
    op.is_counting = len(f) == 1
    for index, elem in enumerate(f):
        if op.is_canceled():
            log.info("canceled")
            break
        op.SetPercentage(index * 100 // len(f))
        try:
            recycle.move_to_recycle_bin(elem, op.is_canceled)
        except recycle.Canceled:
            log.info("canceled while processing %s" % elem)
            break
        except recycle.RecycleError as err:
            log.error("file op error %s %s %s" % (elem, type(err).__name__, err))
            if err.is_access_denied() and not op.elevated:
                appendRetry(op.output, elem)
            else:
                helper.AppendFailed(op, elem, 0, _get_message(err))
            continue
        # end except
        op.output["succeeded"] += 1
    # end ゴミ箱ループ
    op.is_counting = False
    if op.is_canceled():
        op.output["retry"]["target"] = []
    if len(op.output["retry"]["target"]) > 0:
        op.output["retry"]["operation"] = VERB
        retry = len(op.output["retry"]["target"])
    # end リトライあるか
    return retry


def _get_message(err):
    """失敗の理由を返す。昇格したプロセスでは翻訳を使えないので、表示するときに文章にする。"""
    if isinstance(err, recycle.NoRecycleBinError):
        return helper.NO_RECYCLE_BIN
    if isinstance(err, recycle.PermanentlyDeletedError):
        return helper.PERMANENTLY_DELETED
    return helper.UNKNOWN_ERROR


def appendRetry(output, target):
    """リトライするリストに追加する。"""
    output["retry"]["target"].append(target)
