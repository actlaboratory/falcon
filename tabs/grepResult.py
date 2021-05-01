# -*- coding: utf-8 -*-
# Falcon grep result tab
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
grep検索の結果が格納されます。同じファイルで複数のヒットがあった場合、エントリの数が増えていきます。
"""

import globalVars
import lists

from . import searchResultTabBase


class GrepResultTab(searchResultTabBase.SearchResultTabBase):
    """grepの検索結果が表示されているタブ。"""

    blockMenuList = searchResultTabBase.SearchResultTabBase.blockMenuList + [
        "MOVE_FORWARD_TAB",
        "MOVE_TOPFILE",
    ]

    # 内部で利用するリストの種類を定義
    listType = lists.GrepResultList

    def ReadListInfo(self):
        globalVars.app.say(
            _("%(keyword)sのファイル内容検索結果を %(sortkind)sの%(sortad)sで一覧中、 %(max)d個中 %(current)d個目") % {
                'keyword': self.listObject.GetKeywordString(),
                'sortkind': self.listObject.GetSortKindString(),
                'sortad': self.listObject.GetSortAdString(),
                'max': len(
                    self.listObject),
                'current': self.GetFocusedItem() + 1},
            interrupt=True)
