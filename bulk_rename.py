# -*- coding: utf-8 -*-
# Falcon bulk rename rules
# Note: All comments except these top lines will be written in Japanese.

"""正規表現による名前の一括置換で、新しい名前を求めて問題がないかを調べる。画面には依存しない。"""

import os
import re

import fileSystemManager

# 置換結果の状態
STATUS_OK = "ok"
STATUS_UNCHANGED = "unchanged"
STATUS_ERROR = "error"


class RenameTarget:
    """一括置換の対象となる項目"""

    def __init__(self, fullpath: str, is_directory: bool):
        self.fullpath = fullpath
        self.directory = os.path.dirname(fullpath)
        self.basename = os.path.basename(fullpath)
        self.is_directory = is_directory


class RenamePlan:
    """1項目分の置換結果"""

    def __init__(self, target: RenameTarget, new_name: str, status: str, message: str = ""):
        self.target = target
        self.new_name = new_name
        self.status = status
        self.message = message

    @property
    def new_fullpath(self):
        """変更後のフルパス"""
        return os.path.join(self.target.directory, self.new_name)


def compile_pattern(pattern: str, ignore_case: bool):
    """
    検索する正規表現をコンパイルする。
    文法が間違っている場合は re.error を送出する。
    """
    flags = re.IGNORECASE if ignore_case else 0
    return re.compile(pattern, flags)


def make_new_name(regex, replacement: str, name: str, is_directory: bool, include_extension: bool) -> str:
    """
    1つの名前に置換を適用した結果を返す。
    include_extension が False のファイルは、拡張子を除いた部分だけを置換する。
    置換文字列の後方参照が間違っている場合は re.error を送出する。
    """
    if is_directory or include_extension:
        return regex.sub(replacement, name)
    stem, ext = os.path.splitext(name)
    return regex.sub(replacement, stem) + ext


def make_plans(targets: list, pattern: str, replacement: str, ignore_case: bool, include_extension: bool, exists=os.path.exists) -> list:
    """
    すべての対象について新しい名前を求め、問題がないかを調べた結果(RenamePlan のリスト)を返す。
    パターンの文法が間違っている場合は re.error を送出する。
    exists はファイルの存在確認に使う関数(テスト用に差し替えられる)。
    """
    regex = compile_pattern(pattern, ignore_case)
    plans = []
    for target in targets:
        try:
            new_name = make_new_name(regex, replacement, target.basename, target.is_directory, include_extension)
        except (re.error, IndexError) as e:
            plans.append(RenamePlan(target, target.basename, STATUS_ERROR, _("置換文字列が間違っています: %(error)s") % {"error": e}))
            continue
        plans.append(_check_name(target, new_name))
    _check_conflicts(plans, exists)
    return plans


def _check_name(target: RenameTarget, new_name: str) -> RenamePlan:
    """1つの新しい名前について、名前として使えるかを調べる"""
    if new_name == target.basename:
        return RenamePlan(target, new_name, STATUS_UNCHANGED, _("変更なし"))
    if new_name == "":
        return RenamePlan(target, new_name, STATUS_ERROR, _("名前が空になります。"))
    path_type = fileSystemManager.pathTypes.DIRECTORY if target.is_directory else fileSystemManager.pathTypes.FILE
    error = fileSystemManager.ValidationObjectName(os.path.join(target.directory, new_name), path_type, new_name)
    if error:
        return RenamePlan(target, new_name, STATUS_ERROR, error)
    return RenamePlan(target, new_name, STATUS_OK)


def _check_conflicts(plans: list, exists):
    """変更後の名前が、ほかの変更後の名前や既存の項目と重ならないかを調べる。Windows では大文字小文字を区別しない。"""
    # 対象項目の今のパス(名前を変える項目だけ。変えない項目はそのまま残る)
    renaming_paths = {os.path.normcase(p.target.fullpath) for p in plans if p.status == STATUS_OK}
    # 変更後の名前の重複
    new_path_count = {}
    for plan in plans:
        if plan.status == STATUS_OK:
            key = os.path.normcase(plan.new_fullpath)
            new_path_count[key] = new_path_count.get(key, 0) + 1
    for plan in plans:
        if plan.status != STATUS_OK:
            continue
        key = os.path.normcase(plan.new_fullpath)
        if new_path_count[key] > 1:
            plan.status = STATUS_ERROR
            plan.message = _("ほかの項目と同じ名前になります。")
            continue
        if key == os.path.normcase(plan.target.fullpath):
            continue  # 大文字小文字だけの変更
        if key in renaming_paths:
            # 名前を変える別の項目の今の名前と同じ。順番によっては上書きになるので認めない
            plan.status = STATUS_ERROR
            plan.message = _("名前を変更する別の項目の、今の名前と同じです。")
            continue
        if exists(plan.new_fullpath):
            plan.status = STATUS_ERROR
            plan.message = _("同じ名前の項目がすでにあります。")


def count_status(plans: list, status: str) -> int:
    """指定した状態の項目数を返す"""
    return sum(1 for p in plans if p.status == status)
