# -*- coding: utf-8 -*-
# Falcon folder compare
# Note: All comments except these top lines will be written in Japanese.

"""
2つのタブに表示しているフォルダの中身を比べる処理です（FileZilla の「ディレクトリの比較」に当たるもの）。
表示中の一覧の情報（名前・種類・大きさ・更新日時）だけを使い、サーバーやディスクには問い合わせません。
フォルダの中までは比べません。画面には触りません。
"""

import datetime

# 違いの種類
ONLY_HERE = "only_here"
TYPE_DIFFERS = "type_differs"
SIZE_DIFFERS = "size_differs"
NEWER = "newer"

# 更新日時を比べるときに、同じとみなす差（秒）。FAT のファイルの時刻は2秒単位
_DEFAULT_PRECISION = 2


class Difference:
    """違いのある項目"""

    def __init__(self, element, kind):
        # 比べた側（アクティブなタブ）の browsableObjects
        self.element = element
        self.kind = kind


def _is_folder(element):
    # 循環 import を避けるため、クラスではなく属性で判断する
    return type(element).__name__ in ("Folder", "SearchedFolder", "RemoteFolder")


def compare(elements, other_elements, case_sensitive=False):
    """
    elements（比べる側の項目）のうち、other_elements（相手の項目）と違うものを Difference のリストで返す。
    - 相手にない項目
    - 相手では種類（ファイル・フォルダ）が違う項目
    - 大きさが違うファイル
    - 大きさが同じで、こちらのほうが新しいファイル
    case_sensitive=False の場合は、名前の大文字と小文字を区別しない（Windows のフォルダと比べる場合）。
    """
    def key(name):
        return name if case_sensitive else name.lower()

    others = {}
    for other in other_elements:
        others.setdefault(key(other.basename), other)
    differences = []
    for element in elements:
        other = others.get(key(element.basename))
        if other is None:
            differences.append(Difference(element, ONLY_HERE))
            continue
        if _is_folder(element) != _is_folder(other):
            differences.append(Difference(element, TYPE_DIFFERS))
            continue
        if _is_folder(element):
            continue
        size, other_size = getattr(element, "size", -1), getattr(other, "size", -1)
        if size >= 0 and other_size >= 0 and size != other_size:
            differences.append(Difference(element, SIZE_DIFFERS))
            continue
        modified, other_modified = getattr(element, "modDate", None), getattr(other, "modDate", None)
        if modified is None or other_modified is None:
            continue
        precision = max(getattr(element, "precision", _DEFAULT_PRECISION), getattr(other, "precision", _DEFAULT_PRECISION), _DEFAULT_PRECISION)
        try:
            if modified - other_modified >= datetime.timedelta(seconds=precision):
                differences.append(Difference(element, NEWER))
        except TypeError:
            pass  # タイムゾーンの有無が違う日時は比べない
    return differences
