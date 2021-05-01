# -*- coding: utf-8 -*-
# Falcon search result tab
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
検索結果が格納されていきます。一通りのファイル操作を行うことができます。
"""

import globalVars
import lists

from . import searchResultTabBase


class SearchResultTab(searchResultTabBase.SearchResultTabBase):
    """検索結果が表示されているタブ。"""

    blockMenuList = searchResultTabBase.SearchResultTabBase.blockMenuList + [
    ]

    # 内部で利用するリストの種類を定義
    listType = lists.SearchResultList

    # TODO:GoToTopFile(self):

    def ReadListInfo(self):
        globalVars.app.say(
            _("%(keyword)sの検索結果を %(sortkind)sの%(sortad)sで一覧中、 %(max)d個中 %(current)d個目") % {
                'keyword': self.listObject.GetKeywordString(),
                'sortkind': self.listObject.GetSortKindString(),
                'sortad': self.listObject.GetSortAdString(),
                'max': len(
                    self.listObject),
                'current': self.GetFocusedItem() + 1},
            interrupt=True)
