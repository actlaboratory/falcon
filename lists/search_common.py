# -*- coding: utf-8 -*-
# Falcon search result list common functions
# Note: All comments except these top lines will be written in Japanese.

"""
ファイル名検索・ファイル内容検索のリストに共通の処理。
lists/searchResultBase.py は他のプロジェクトと共通のため変更せず、ここで不具合を直す。
"""

import re
import unicodedata

import pywintypes

import globalVars

from .searchResultBase import SearchResultBase

# ファイル一覧の終わりを表す印。ファイル名に使えない文字を含むので、実在するファイルと区別できる
SEARCH_EOL = "<eol>"

# 1回の検索ステップでヒットさせる最大件数
_HITS_PER_STEP = 100


def normalize_text(text):
    """全角・半角などの違いをなくした文字列を返す。正規表現を使わない検索で、両方をこれでそろえて比べる。"""
    return unicodedata.normalize("NFKC", text)


def original_index(text, normalized_index):
    """normalize_text(text) の中の位置 normalized_index が、元の text のどの位置にあたるかを返す。"""
    low = 0
    high = len(text)
    while low < high:
        mid = (low + high) // 2
        if len(normalize_text(text[:mid])) < normalized_index:
            low = mid + 1
        else:
            high = mid
    return low


def make_pattern(keyword, is_regular_expression):
    """
    キーワードから検索に使う正規表現を作る。
    正規表現を使わない場合は、* と ? をワイルドカードとして扱い、それ以外の文字はそのまま探す。
    """
    if is_regular_expression:
        return re.compile(keyword, re.IGNORECASE)
    keyword = normalize_text(keyword)
    parts = []
    for c in keyword:
        if c == "*":
            parts.append(".*")
        elif c == "?":
            parts.append(".")
        else:
            parts.append(re.escape(c))
    return re.compile("".join(parts), re.IGNORECASE | re.DOTALL)


def has_wildcard(keyword):
    """キーワードにワイルドカード(* か ?)が含まれていれば True を返す。"""
    return "*" in keyword or "?" in keyword


class SearchResultCommon(SearchResultBase):
    """SearchResultBase の不具合を直した、検索結果のリストの共通部分。"""

    def _initKeyword(self, keyword, isRegularExpression, silent):
        """キーワードを正規表現にする。読み上げには、変換前のキーワードを使う。"""
        self.keyword_string = keyword
        self.is_regular_expression = isRegularExpression
        self.keyword = make_pattern(keyword, isRegularExpression)
        if not silent:
            globalVars.app.say(
                _("%(keyword)sの検索結果 %(dir)s から") % {"keyword": keyword, "dir": self.rootDirectory})

    def _match(self, text, whole=False):
        """
        text からキーワードを探し、見つかれば (re.Match, 探した文字列) を返す。見つからなければ None。
        whole=True のときは、text 全体が一致する場合だけ見つかったことにする。
        正規表現を使わない場合は、全角・半角などの違いを無視する。
        """
        find = self.keyword.fullmatch if whole else self.keyword.search
        m = find(text)
        if m:
            return m, text
        if not self.is_regular_expression:
            normalized = normalize_text(text)
            if normalized != text:
                m = find(normalized)
                if m:
                    return m, normalized
        return None

    def _performSearchStep(self, taskState):
        """
        検索を1ステップ実行する。戻り値は SearchResultBase と同じ。
        SearchResultBase では、ファイル一覧の取得が終わっていないうちに一覧の最後まで来ると、
        次のステップで同じファイルをもう一度調べて結果が重複していたため、調べた位置を毎回覚える。
        """
        ret_list = []
        hit = 0
        while self.searched_index < len(self.searches):
            if taskState.canceled:
                return False, -1  # 途中でキャンセル
            path = self.searches[self.searched_index]
            if path == SEARCH_EOL:
                self.finished = True
                globalVars.app.play_sound("complete.ogg")
                globalVars.app.say(_("検索終了、%(item)d件ヒットしました。") % {"item": len(self)})
                return True, ret_list
            self.searched_index += 1
            try:
                hit += self.HitTest(path, ret_list)
            except (OSError, pywintypes.error) as err:
                # 一覧を取得した後で消されたファイルや、読めないファイルは飛ばす
                self.log.warning("Cannot check %s while searching (%s)" % (path, err))
            if hit >= _HITS_PER_STEP:
                break
        return False, ret_list

    def IsWaitingForFileList(self):
        """取得済みのファイルをすべて調べ終わり、ファイル一覧の続きを待っている状態なら True を返す。"""
        return not self.finished and self.searched_index >= len(self.searches)

    def Update(self):
        """同じ条件で検索をやり直す準備をする。"""
        return self.Initialize(
            self.rootDirectory,
            self.searches,
            self.keyword_string,
            self.is_regular_expression,
            True)
