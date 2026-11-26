# -*- coding: utf-8 -*-
# Falcon grep results list object
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2021 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import os
import wx

import browsableObjects
import errorCodes
import misc

from .search_common import SearchResultCommon, original_index
from .constants import *

# プレビューに出す、ヒットした位置より前の文字数と、全体の文字数
_PREVIEW_BEFORE = 10
_PREVIEW_LENGTH = 25


class GrepResultList(SearchResultCommon):
    """grep検索の結果を扱うリスト。"""

    def __init__(self):
        super().__init__()
        self.supportedSorts = [
            SORT_TYPE_BASENAME,
            SORT_TYPE_HITLINE,
            SORT_TYPE_PREVIEW,
            SORT_TYPE_HITCOUNT,
            SORT_TYPE_FILESIZE,
            SORT_TYPE_MODDATE,
            SORT_TYPE_ATTRIBUTES,
            SORT_TYPE_TYPESTRING]
        self.columns = {
            _("ファイル名"): wx.LIST_FORMAT_LEFT,
            _("行"): wx.LIST_FORMAT_RIGHT,
            _("プレビュー"): wx.LIST_FORMAT_LEFT,
            _("ヒット件数"): wx.LIST_FORMAT_RIGHT,
            _("サイズ"): wx.LIST_FORMAT_RIGHT,
            _("更新"): wx.LIST_FORMAT_LEFT,
            _("属性"): wx.LIST_FORMAT_LEFT,
            _("種類"): wx.LIST_FORMAT_LEFT
        }
        self.results = []
        self.lists = [self.results]

    def Initialize(
            self,
            rootDirectory,
            searches=[],
            keyword="",
            isRegularExpression=False,
            silent=False):
        """与えられたファイル名のリストから、条件に一致する項目を抽出する。"""
        self.ClearCache()
        if isinstance(
                rootDirectory,
                list):  # パラメータがリストなら、browsableObjects のリストとして処理刷る(ファイルリストを取得しないでコピーする)
            for elem in rootDirectory:
                self.results.append(elem)
            # end for
            return errorCodes.OK
        self.rootDirectory = rootDirectory
        self.searches = searches
        self._initKeyword(keyword, isRegularExpression, silent)
        self._initSearch()

    def HitTest(self, path, ret_list):
        """_performSearchStepから呼ばれ、与えられたpathのファイルが検索にヒットするならリスト追加する"""
        fullpath = os.path.join(self.rootDirectory, path)
        ext = os.path.splitext(path)[1][1:]
        if ext == "" or not misc.isDocumentExt(ext) or not os.path.isfile(fullpath):
            return 0
        text = misc.ExtractText(fullpath)
        if text is None:  # 読み取れないファイルはヒットしない扱い
            return 0
        # 改行コードの違いで行がずれたり、プレビューに CR が入ったりしないようにそろえる
        content = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        fileobj = None  # 複数ヒットでファイルオブジェクトを生成し続けないようにキャッシュする
        hitobjects = []
        for ln, line in enumerate(content, 1):
            result = self._match(line)
            if result is None:
                continue
            m, searched = result
            start = m.start()
            if searched is not line:
                # 全角・半角などをそろえた文字列でヒットした場合も、プレビューは元の文字列から作る
                start = original_index(line, start)
            preview_start = max(0, start - _PREVIEW_BEFORE)
            preview = line[preview_start:preview_start + _PREVIEW_LENGTH]
            if not fileobj:
                fileobj = self._MakeObject(browsableObjects.File, fullpath)
            obj = browsableObjects.GrepItem()
            obj.Initialize(ln, preview, fileobj)
            hitobjects.append(obj)
        # end 行数ごとに検索
        for elem in hitobjects:
            elem.SetHitCount(len(hitobjects))
        # end 最終的なヒットカウントを設定
        self.results.extend(hitobjects)
        ret_list.extend(hitobjects)
        return len(hitobjects)

    def _GetJumpKey(self, index):
        """
                デフォルトの先頭文字単位ではなく、見つかったファイル単位で動く
        """
        sortType = self.supportedSorts[self.sortCursor]
        if sortType == SORT_TYPE_BASENAME:
            return self.GetElement(index).fullpath
        else:
            return super()._GetJumpKey(index)
