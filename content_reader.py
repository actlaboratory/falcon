# -*- coding: utf-8 -*-
# Falcon content reader
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.

"""
ファイルの内容のプレビュー・先頭/末尾の読み上げを行います。
tabs/base.py の Preview・ReadHeader・ReadFooter は、項目にフォーカスがない場合や文書を読み取れない場合に例外になるため、
tabs/base.py を変更せずに済むよう、メニューからはこちらを呼びます。
"""

import constants
import globalVars
import misc


def preview(tab):
    """フォーカスされているファイルをプレビューする。音声ファイルの再生はタブに任せる。"""
    path = _get_focused_path(tab)
    if path is None:
        return
    ext = _get_ext(path)
    if ext in constants.SUPPORTED_AUDIO_FORMATS:
        tab.Preview()
    elif misc.isDocumentExt(ext):
        text = _extract_text(path)
        if text is not None:
            globalVars.app.say(text, interrupt=True)
    else:
        globalVars.app.say(_("プレビューに対応していないファイル形式です。"), interrupt=True)


def read_header(tab):
    """フォーカスされている文書の先頭を、設定された行数だけ読み上げる。"""
    lines = _get_document_lines(tab)
    if lines is None:
        return
    ln = globalVars.app.settings.get_int("preview", "header_line_count", 10, 1, 100)
    prefix = _("先頭%(ln)d行") % {"ln": ln}
    globalVars.app.say("%s %s" % (prefix, "\n".join(lines[:ln])), interrupt=True)


def read_footer(tab):
    """フォーカスされている文書の末尾を、設定された行数だけ読み上げる。"""
    lines = _get_document_lines(tab)
    if lines is None:
        return
    ln = globalVars.app.settings.get_int("preview", "footer_line_count", 10, 1, 100)
    prefix = _("末尾%(ln)d行") % {"ln": ln}
    globalVars.app.say("%s %s" % (prefix, "\n".join(lines[-ln:])), interrupt=True)


def _get_document_lines(tab):
    """フォーカスされている文書を行のリストで返す。読み上げられない場合は理由を読み上げてNoneを返す。"""
    path = _get_focused_path(tab)
    if path is None:
        return None
    if not misc.isDocumentExt(_get_ext(path)):
        globalVars.app.say(_("ドキュメントファイルではありません。"), interrupt=True)
        return None
    text = _extract_text(path)
    if text is None:
        return None
    return text.split("\n")


def _get_focused_path(tab):
    """フォーカスされている項目のパスを返す。項目がない場合は読み上げてNoneを返す。"""
    elem = tab.GetFocusedElement()
    if elem is None:
        globalVars.app.say(_("項目なし"), interrupt=True)
        return None
    return elem.fullpath


def _get_ext(path):
    """拡張子を小文字で返す。"""
    return path.split(".")[-1].lower()


def _extract_text(path):
    """文書のテキストを返す。読み取れない場合は読み上げてNoneを返す。"""
    text = misc.ExtractText(path)
    if text is None:
        globalVars.app.say(_("読み取れません"), interrupt=True)
    return text
