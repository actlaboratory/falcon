# -*- coding: utf-8 -*-
# Falcon key map management
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2021 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

"""
falconのショートカットキーの管理。

キー名とキーコードの対応は viewkit の表(viewkit.shortcut.str2key)を使う。
viewkit のショートカットキー管理は、falcon で次のことができないため、このモジュールで独自に管理している。
- ALT+F4・SHIFT+F10・ESCAPE など、システムが使うキーをアプリケーション自身が割り当てる
- ウィンドウごとに、使えるキーを追加・制限する(矢印キーを単独で使うなど)
- タブの種類によって、同じキーを別の機能に割り当てる(Delete キーがファイル一覧ではゴミ箱、ドライブ一覧では取り外しなど)
"""

from logging import getLogger

import wx

from viewkit.shortcut import str2key as key_table

import browsableObjects
import constants
import menuItemsStore
import tabs.navigator  # 全てのタブのモジュールを、循環importにならない順序で読み込む
import views.menuBlocker

# キー名からキーコードへの対応表
KEY_CODES = key_table.str2key

# キーの区切り文字
KEY_SEPARATOR = "/"
MODIFIER_SEPARATOR = "+"

# ショートカットキーとして使える修飾キー
_MODIFIER_FLAGS = {
    "CTRL": wx.ACCEL_CTRL,
    "ALT": wx.ACCEL_ALT,
    "SHIFT": wx.ACCEL_SHIFT,
}

# OSなどが使っているため、常に設定できないキーの組み合わせ
_ALWAYS_DISABLED = (
    "CTRL+ESCAPE",  # スタートメニュー
    "CTRL+SHIFT+ESCAPE",  # タスクマネージャ
    "CTRL+WINDOWS+RETURN",  # ナレーターの起動と終了
    "ALT+SHIFT+PRINTSCREEN",  # ハイコントラストの切り替え
    "ALT+ESCAPE",  # 最前面ウィンドウの最小化
    "ALT+TAB",  # ウィンドウ間の移動
    "ALT+SHIFT+TAB",  # ウィンドウ間の移動
)

# 文字入力ができるウィンドウでは設定できないキーの組み合わせ
_DISABLED_WITH_CHAR_INPUT = (
    "CTRL+INSERT",  # コピー
    "SHIFT+INSERT",  # 貼り付け
    "CTRL+Z",  # 元に戻す
    "CTRL+X",  # 切り取り
    "CTRL+C",  # コピー
    "CTRL+V",  # 貼り付け
    "CTRL+A",  # すべて選択
    "CTRL+Y",  # やり直し
    "CTRL+F7",  # 単語登録(日本語変換時のみ)
    "CTRL+F10",  # IMEメニュー表示(日本語変換時のみ)
)

# ユーザが独自に設定することが望ましくないキーの組み合わせ
_DISABLED_FOR_USER = (
    "APPLICATIONS",  # コンテキストメニューの表示
    "SHIFT+F10",  # コンテキストメニューの表示
    "F10",  # ALTキーの代わり
    "ESCAPE",  # 操作の取り消し
    "ALT+F4",  # アプリケーションの終了
    "SPACE",  # ボタンの押下
    "ALT+SPACE",  # リストビュー等で全ての選択を解除
)


def _normalize(key_string: str) -> str:
    return key_string.upper()


class KeyFilter:
    """利用できるショートカットキーを制限するためのフィルタ"""

    def __init__(self, allow_char_input: bool, is_system: bool, char_key_standalone: bool = False):
        """
        allow_char_input: そのウィンドウで文字入力ができるか。Falseなら、Home・BS などを単独でショートカットに使える
        is_system: 開発者が設定する場合はTrue、ユーザが設定する場合はFalse。
            Falseなら、ユーザが指定することが望ましくないキー(ESCAPE、ALT+F4 など)を使えなくする
        char_key_standalone: 英数字や記号のキーを単独で使えるようにするか。インクリメンタルサーチ等と競合するため原則False
        """
        self.last_error = ""  # 最後に検知したエラーの原因
        self.modifier_keys = set(_MODIFIER_FLAGS.keys())  # 有効な修飾キー
        self.standalone_keys = set()  # 単独または修飾キーとの組み合わせで利用可能
        self.with_modifier_keys = set()  # 修飾キーとの組み合わせで利用可能
        self.no_shift_keys = set()  # SHIFTキー以外の修飾キーとの組み合わせで利用可能
        self.disabled_patterns = []  # 無効なキーの組み合わせ

        self.standalone_keys |= key_table.str2FunctionKey.keys()
        self.standalone_keys |= key_table.str2SpecialKey.keys()
        for pattern in _ALWAYS_DISABLED:
            self.add_disabled_pattern(pattern)

        if allow_char_input:
            # 文字入力に関わる共通のショートカットは設定不可
            for pattern in _DISABLED_WITH_CHAR_INPUT:
                self.add_disabled_pattern(pattern)
            # 単独で文字入力の制御に利用されるので修飾キー必須
            self.with_modifier_keys |= key_table.str2InputControlKey.keys()
        else:
            # 単独で文字入力の制御に利用されるが、それがないなら単独利用可能
            self.standalone_keys |= key_table.str2InputControlKey.keys()

        if is_system:
            self.standalone_keys |= key_table.str2GenericKey.keys()
        else:
            for pattern in _DISABLED_FOR_USER:
                self.add_disabled_pattern(pattern)
            self.with_modifier_keys |= key_table.str2GenericKey.keys()

        if char_key_standalone:
            self.standalone_keys |= key_table.str2CharacterKey.keys()
        else:
            self.no_shift_keys |= key_table.str2CharacterKey.keys()

    def add_disabled_pattern(self, pattern: str):
        """設定できないキーの組み合わせを追加する"""
        keys = _normalize(pattern).split(MODIFIER_SEPARATOR)
        for key in keys:
            if key not in KEY_CODES:
                raise ValueError(_("%s は存在しないキーです。") % key)
        self.disabled_patterns.append(set(keys))

    def add_standalone_keys(self, keys):
        """単独でも使えるキーを追加する"""
        for key in ([keys] if isinstance(keys, str) else keys):
            key = _normalize(key)
            if key not in KEY_CODES:
                raise ValueError(_("%s は存在しないキーです。") % key)
            if {key} in self.disabled_patterns:
                self.disabled_patterns.remove({key})
            for group in (self.with_modifier_keys, self.modifier_keys, self.no_shift_keys):
                group.discard(key)
            self.standalone_keys.add(key)

    def check(self, key_string: str) -> bool:
        """単一のキーの組み合わせ(例: CTRL+R)が使えるかを返す。使えない場合は last_error に理由が入る"""
        self.last_error = ""
        if key_string == "":
            self.last_error = _("キーが指定されていません。")
            return False

        keys = _normalize(key_string).split(MODIFIER_SEPARATOR)
        has_modifier = False
        has_shift = False
        standalone_count = 0
        with_modifier_count = 0
        no_shift_count = 0
        for key in keys:
            if key in self.modifier_keys:
                if key == "SHIFT":
                    has_shift = True
                else:
                    has_modifier = True
            elif key in self.standalone_keys:
                standalone_count += 1
            elif key in self.with_modifier_keys:
                with_modifier_count += 1
            elif key in self.no_shift_keys:
                no_shift_count += 1
            else:
                self.last_error = _("%s は使用できないキーです。") % key
                return False

        # 組み合わせの妥当性確認
        if len(keys) == 1:
            if standalone_count > 0:
                return True
            if has_modifier or has_shift:
                self.last_error = _("修飾キーのみのパターンは設定できません。")
            else:
                self.last_error = _("このキーは修飾キーと合わせて指定する必要があります。")
            return False

        # ２つ以上が指定されている場合
        if standalone_count + with_modifier_count + no_shift_count > 1:
            self.last_error = _("修飾キーでないキーを複数指定することはできません。")
            return False
        if standalone_count + with_modifier_count + no_shift_count == 0:
            self.last_error = _("修飾キーのみの組み合わせは指定できません。")
            return False
        if no_shift_count > 0 and not has_modifier:
            self.last_error = _("このキーは、SHIFTキー以外の修飾キーと合わせて指定する必要があります。")
            return False
        if set(keys) in self.disabled_patterns:
            self.last_error = _("この組み合わせは別の用途で予約されているため、利用できません。")
            return False
        return True

    def get_usable_keys(self) -> list:
        """このフィルタで使えるキーの名前の一覧を返す"""
        return [*self.modifier_keys, *self.standalone_keys, *self.with_modifier_keys, *self.no_shift_keys]


def create_main_window_filter() -> KeyFilter:
    """メインウィンドウ(ファイル一覧など)で使うキーフィルタを作る"""
    key_filter = KeyFilter(allow_char_input=False, is_system=True)
    key_filter.add_standalone_keys(("LEFTARROW", "RIGHTARROW", "NUMPAD_DIVIDE", "NUMPAD_MULTIPLY"))
    return key_filter


class ShortcutEntry(wx.AcceleratorEntry):
    """
    機能の識別子を持つアクセラレータエントリ。
    比較はキーの組み合わせだけで行い、割り当てられた機能は無視する。
    """

    def __init__(self, flags, key_code, command, identifier=""):
        super().__init__(flags, key_code, command)
        self.identifier = identifier

    def __eq__(self, other):
        if other is None or type(self) is not type(other):
            return False
        return self.GetFlags() == other.GetFlags() and self.GetKeyCode() == other.GetKeyCode()

    def __hash__(self):
        return hash((self.GetFlags(), self.GetKeyCode()))

    def __repr__(self):
        return "<ShortcutEntry %s>" % self.identifier


def make_entry(identifier: str, key_string: str, key_filter: KeyFilter = None, log=None):
    """機能の識別子と、/区切りでない単一のキー(例: CTRL+R)から ShortcutEntry を作る。作れなければ None を返す"""
    log = log or getLogger("%s.keymap" % constants.LOG_PREFIX)
    keys = _normalize(key_string).split(MODIFIER_SEPARATOR)
    modifiers = dict(_MODIFIER_FLAGS)
    if key_filter is not None and "WINDOWS" in key_filter.modifier_keys:
        modifiers["WINDOWS"] = wx.MOD_WIN

    flags = 0
    modifier_count = 0
    for name, value in modifiers.items():
        if name in keys[:-1]:
            flags |= value
            modifier_count += 1
    # 修飾キーのみのもの、修飾キーでないキーが複数含まれるものはダメ
    if len(keys) - modifier_count != 1:
        log.warning("%s is invalid pattern." % key_string)
        return None
    key_name = keys[-1]
    if key_name not in KEY_CODES:  # 存在しないキーの指定はエラー
        log.warning("keyname %s is wrong" % key_name)
        return None
    if key_filter is not None and not key_filter.check(key_string):
        log.warning("%s(%s): %s" % (identifier, key_string, key_filter.last_error))
        return None
    identifier = identifier.upper()
    return ShortcutEntry(flags, KEY_CODES[key_name], menuItemsStore.getRef(identifier), identifier)


def permit_conflict(entries: list, log=None) -> bool:
    """
    同じキーが割り当てられた機能(entries)が、タブの種類や選択項目によって同時に有効にならないかを調べる。
    同時に有効になることがなければ、キーの重複を許してTrueを返す。
    """
    log = log or getLogger("%s.keymap" % constants.LOG_PREFIX)
    tab_type_condition = views.menuBlocker.tabTypeBlockList
    item_type_condition = views.menuBlocker.selectedItemTypeBlockList
    count_condition = views.menuBlocker.selectedItemCountBlockList

    used_flags = 0
    for identifier in [entry.identifier for entry in entries]:
        # 各ビットが「その状況でこの機能が有効になる」ことを表す
        flags = 0
        # ファイルリストタブ
        if identifier not in tab_type_condition[tabs.fileList.FileListTab]:
            if identifier not in item_type_condition[browsableObjects.File]:
                flags |= 1
            if identifier not in item_type_condition[browsableObjects.Folder]:
                flags |= 2
            if identifier not in count_condition[0]:
                flags |= 4
        # ストリームリストタブ
        if identifier not in tab_type_condition[tabs.streamList.StreamListTab]:
            flags |= 8
        # ドライブリストタブ
        if identifier not in tab_type_condition[tabs.driveList.DriveListTab]:
            if identifier not in item_type_condition[browsableObjects.Drive]:
                flags |= 16
            if identifier not in item_type_condition[browsableObjects.NetworkResource]:
                flags |= 32
            if identifier not in count_condition[0]:
                flags |= 64
        # GrepResultTab
        if identifier not in tab_type_condition[tabs.grepResult.GrepResultTab]:
            flags |= 128
        # SearchResultTab
        if identifier not in tab_type_condition[tabs.searchResult.SearchResultTab]:
            if identifier not in item_type_condition[browsableObjects.SearchedFile]:
                flags |= 256
            if identifier not in item_type_condition[browsableObjects.SearchedFolder]:
                flags |= 512
            if identifier not in count_condition[0]:
                flags |= 1024

        if flags & used_flags != 0:
            log.warning("key conflicted. %s is conflict in %s" % (identifier, entries))
            return False
        used_flags |= flags
    log.debug("key not conflicted. %s" % entries)
    return True


class Keymap:
    """
    1つのウィンドウのショートカットキーを管理する。
    同じキーを複数の機能に割り当てる場合は、そのキー専用のrefでアクセラレータテーブルに登録し、
    そのrefのメニューイベントを受けたときに、元の機能のrefへ振り分ける(is_shared_ref, get_original_refs)。
    """

    def __init__(self, key_filter: KeyFilter, conflict_checker=permit_conflict):
        self.log = getLogger("%s.keymap" % constants.LOG_PREFIX)
        self.key_filter = key_filter
        self.conflict_checker = conflict_checker
        self.entries = []  # 登録したShortcutEntry
        self.key_strings = {}  # 機能の識別子 -> "/"区切りのキー文字列
        self.errors = {}  # 登録できなかった 機能の識別子 -> キー文字列
        self._shared_refs = {}  # 重複キー用のref -> 元の機能のrefのリスト

    def load(self, shortcuts: dict):
        """{機能の識別子: "/"区切りのキー文字列} の辞書からまとめて登録する。空文字列は無視する"""
        for identifier, key_string in shortcuts.items():
            if key_string:
                self.add(identifier, key_string)

    def add(self, identifier: str, key_string: str):
        """重複をチェックしながら、機能にショートカットキーを追加する"""
        identifier = identifier.upper()
        for key in key_string.split(KEY_SEPARATOR):
            entry = make_entry(identifier, key, self.key_filter, self.log)
            if entry is None:
                self._add_error(identifier, key_string, "make entry failed")
                continue

            # キーの重複確認
            conflicts = [e for e in self.entries if e == entry]
            if conflicts:
                conflicts.append(entry)
                if not (self.conflict_checker and self.conflict_checker(conflicts, self.log)):
                    self._add_error(identifier, key_string, "conflict")
                    continue
                self._share_key(conflicts)
            else:
                self.entries.append(entry)

            # get_key_stringに備えて記録
            if identifier in self.key_strings:
                self.key_strings[identifier] += KEY_SEPARATOR + key
            else:
                self.key_strings[identifier] = key

    def _add_error(self, identifier, key_string, reason):
        self.log.warning("Cannot add %s=%s reason=%s" % (identifier, key_string, reason))
        self.errors[identifier] = key_string

    def _share_key(self, entries):
        """重複したキーを、そのキー専用のrefに置き換えて登録する。entriesの最後は新しく追加するもの。"""
        first = entries[0]
        shared_ref = menuItemsStore.getRef("keymap_" + first.ToRawString())
        # 登録済みのものをいったん削除し、機能ごとに専用のrefで登録し直す
        # (次に同じキーが追加されたときの重複確認で、全ての機能を調べられるようにするため)
        self.entries = [e for e in self.entries if e != first]
        original_refs = []
        for entry in entries:
            self.entries.append(ShortcutEntry(first.GetFlags(), first.GetKeyCode(), shared_ref, entry.identifier))
            ref = menuItemsStore.getRef(entry.identifier)
            if ref not in original_refs:
                original_refs.append(ref)
        self._shared_refs[shared_ref] = original_refs

    def pop_errors(self) -> dict:
        """登録できなかったものを返し、記録を消す"""
        errors = self.errors
        self.errors = {}
        return errors

    def get_key_string(self, identifier: str):
        """機能に割り当てられたキーの文字列を返す。なければNone"""
        return self.key_strings.get(identifier.upper())

    def apply(self, window: wx.Window):
        """ウィンドウにアクセラレータテーブルを設定する"""
        window.SetAcceleratorTable(wx.AcceleratorTable(self.entries))

    def is_shared_ref(self, ref: int) -> bool:
        """重複キー用のrefかを返す"""
        return ref in self._shared_refs

    def get_original_refs(self, ref: int) -> list:
        """重複キー用のrefに対応する、元の機能のrefのリストを返す"""
        return self._shared_refs[ref]
