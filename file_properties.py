# -*- coding: utf-8 -*-
# Falcon file properties
# Note: All comments except these top lines will be written in Japanese.

"""
ファイルのプロパティ情報（エクスプローラーのプロパティの「詳細」タブにある項目）を読み書きする。

Windows のプロパティシステム（IPropertyStore）を使う。表示する項目は、ファイルの種類ごとに
登録されている一覧（System.PropList.FullDetails）に従うので、ファイルの種類によって項目が変わる。
書き込めるかどうかは、ファイルの種類のプロパティハンドラーが書き込みに対応しているかによる。
作成日時と更新日時はプロパティハンドラーでは書き換えられないので、SetFileTime で変更する。

load() と save() は時間がかかることがあるので、background_wait.run() で別スレッドから呼ぶ。
画面の部品は扱わない。
"""

import datetime
import logging
import re

import pythoncom
import pywintypes
import win32file

from win32com.propsys import propsys, pscon
from win32com.shell import shell

log = logging.getLogger("falcon.file_properties")

# IShellItem2.GetPropertyStore に渡す GETPROPERTYSTOREFLAGS
_GPS_DEFAULT = 0
_GPS_READWRITE = 2

# PROPDESC_TYPE_FLAGS
_PDTF_ISINNATE = 0x2  # ファイルから計算される値で、変更できない
_PDTF_ISGROUP = 0x4  # 項目ではなく、分類の見出し
_PDTF_ALL = 0x7fffffff  # 0xffffffff は pywin32 が long に変換できない

# PROPENUMTYPE
_PET_DISCRETEVALUE = 0
_PET_RANGEDVALUE = 1

_FILE_WRITE_ATTRIBUTES = 0x100

# 作成日時・更新日時のプロパティ名。プロパティハンドラーではなく SetFileTime で変更する
DATE_CREATED = "System.DateCreated"
DATE_MODIFIED = "System.DateModified"
FILE_TIME_NAMES = (DATE_CREATED, DATE_MODIFIED)

# プロパティハンドラーが書き込みに対応していないときの HRESULT
_UNSUPPORTED_ERRORS = (
    -2147467259,  # E_FAIL
    -2147467262,  # E_NOINTERFACE
    -2147221164,  # REGDB_E_CLASSNOTREG
)

# 値の種類
KIND_TEXT = "text"
KIND_TEXT_LIST = "text_list"  # 複数の文字列。「;」で区切って入力する
KIND_INTEGER = "integer"
KIND_DECIMAL = "decimal"
KIND_DATE = "date"
KIND_CHOICE = "choice"  # 決められた値から選ぶ
KIND_OTHER = "other"  # 表示のみ

# 整数の型と、とれる値の範囲
_INTEGER_RANGES = {
    pythoncom.VT_I2: (-2 ** 15, 2 ** 15 - 1),
    pythoncom.VT_I4: (-2 ** 31, 2 ** 31 - 1),
    pythoncom.VT_I8: (-2 ** 63, 2 ** 63 - 1),
    pythoncom.VT_UI1: (0, 2 ** 8 - 1),
    pythoncom.VT_UI2: (0, 2 ** 16 - 1),
    pythoncom.VT_UI4: (0, 2 ** 32 - 1),
    pythoncom.VT_UI8: (0, 2 ** 64 - 1),
}

# 日時を入力・表示する書式
DATE_FORMAT = "%Y/%m/%d %H:%M:%S"
# 入力できる日時の形（年/月/日 時:分:秒。時刻と秒は省略できる。区切りは「/」か「-」。日付の後の「(月)」などの曜日は無視する）
# strptime は使わない。wxPython がロケールを「ja-JP」にすると、Python の locale が解釈できずに失敗するため
_DATE_INPUT_PATTERN = re.compile(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})(?:\([^)]*\))?(?:\s+(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?)?")

# 表示用の文字列に入る、文字の向きの制御文字。読み上げの邪魔になるので取り除く
_DIRECTION_MARKS = dict.fromkeys(map(ord, "\u200e\u200f\u202a\u202b\u202c\u202d\u202e"))

# 複数の値の区切り（エクスプローラーと同じ）
LIST_SEPARATOR = "; "


class PropertyItem:
    """プロパティの1項目"""

    def __init__(self, name, label, group, kind, var_type, value, text, editable, choices=None):
        # プロパティの名前（System.Author など）
        self.name = name
        # 表示名
        self.label = label
        # 分類の表示名
        self.group = group
        # 値の種類（KIND_*）
        self.kind = kind
        # PROPVARIANT の型（VT_*）
        self.var_type = var_type
        # 値。値がなければ None。日時はローカル時刻の datetime（タイムゾーン付き）
        self.value = value
        # 表示用の文字列
        self.text = text
        # 変更できるか
        self.editable = editable
        # KIND_CHOICE のとき、(値, 表示名) の一覧。先頭は値なし (None, "なし")
        self.choices = choices or []


class FileProperties:
    """load() の結果"""

    def __init__(self, path, items, writable, write_error):
        self.path = path
        self.items = items
        # プロパティハンドラーで書き込めるか（更新日時は別）
        self.writable = writable
        # 書き込めない理由（writable が False のとき）。種類として書き込みに対応していなければ空
        self.write_error = write_error

    def get_item(self, name):
        """名前を指定して項目を返す。なければ None"""
        for prop in self.items:
            if prop.name == name:
                return prop
        return None


def get_error_message(error):
    """例外から、利用者に見せるエラーの説明を作る"""
    if isinstance(error, pywintypes.com_error):
        return error.strerror or str(error.hresult)
    if isinstance(error, pywintypes.error):
        return error.strerror
    return str(error)


def _clean_text(text):
    """表示用の文字列から制御文字を取り除く"""
    return (text or "").translate(_DIRECTION_MARKS).strip()


def _to_local(value):
    """プロパティから得た日時（UTC）を、ローカル時刻にする"""
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.timezone.utc)
    return datetime.datetime.fromtimestamp(value.timestamp()).astimezone()


def _get_kind(var_type):
    """PROPVARIANT の型から、値の種類を決める"""
    if var_type == pythoncom.VT_LPWSTR or var_type == pythoncom.VT_BSTR:
        return KIND_TEXT
    if var_type == pythoncom.VT_VECTOR | pythoncom.VT_LPWSTR:
        return KIND_TEXT_LIST
    if var_type in _INTEGER_RANGES:
        return KIND_INTEGER
    if var_type == pythoncom.VT_R8 or var_type == pythoncom.VT_R4:
        return KIND_DECIMAL
    if var_type == pythoncom.VT_FILETIME:
        return KIND_DATE
    if var_type == pythoncom.VT_BOOL:
        return KIND_CHOICE
    return KIND_OTHER


def _get_choices(description, var_type):
    """決められた値から選ぶ項目なら、(値, 表示名) の一覧を返す。そうでなければ None。"""
    if var_type == pythoncom.VT_BOOL:
        return [(None, _("なし")), (True, _("はい")), (False, _("いいえ"))]
    try:
        enum_list = description.GetEnumTypeList(propsys.IID_IPropertyEnumTypeList)
    except pywintypes.com_error:
        return None
    choices = [(None, _("なし"))]
    for i in range(enum_list.GetCount()):
        enum_type = enum_list.GetAt(i, propsys.IID_IPropertyEnumType)
        if enum_type.GetEnumType() not in (_PET_DISCRETEVALUE, _PET_RANGEDVALUE):
            continue
        try:
            choices.append((enum_type.GetValue().GetValue(), _clean_text(enum_type.GetDisplayText())))
        except pywintypes.com_error:
            continue
    if len(choices) == 1:
        return None
    return choices


def _find_choice(choices, description, prop_value):
    """今の値に当たる選択肢の値を返す。見つからなければ今の値をそのまま返す"""
    value = prop_value.GetValue()
    for choice_value, dummy in choices:
        if choice_value == value:
            return choice_value
    # 範囲で決まる選択肢（評価など）は、範囲に入るものを探す
    try:
        enum_list = description.GetEnumTypeList(propsys.IID_IPropertyEnumTypeList)
        enum_type = enum_list.GetAt(enum_list.FindMatchingIndex(prop_value), propsys.IID_IPropertyEnumType)
        return enum_type.GetValue().GetValue()
    except pywintypes.com_error:
        return value


def _check_writable(item):
    """プロパティハンドラーで書き込めるかを調べ、(書き込めるか, できない理由) を返す"""
    try:
        store = item.GetPropertyStore(_GPS_READWRITE, propsys.IID_IPropertyStore)
    except pywintypes.com_error as e:
        log.debug("cannot open the property store for writing: %s" % e)
        if e.hresult in _UNSUPPORTED_ERRORS:
            return False, ""
        return False, get_error_message(e)
    del store  # 読み取り用のストアと同時に開くと止まることがあるので、すぐに閉じる
    return True, ""


def _make_item(description, store, group, writable):
    """プロパティの説明と値から PropertyItem を作る。表示しない項目なら None"""
    key = description.GetPropertyKey()
    name = description.GetCanonicalName()
    flags = description.GetTypeFlags(_PDTF_ALL)
    var_type = description.GetPropertyType()
    try:
        prop_value = store.GetValue(key)
    except pywintypes.com_error:
        prop_value = None
    has_value = prop_value is not None and prop_value.vt != pythoncom.VT_EMPTY

    kind = _get_kind(var_type)
    if name in FILE_TIME_NAMES:
        editable = has_value  # 作成日時・更新日時はどのファイルでも変更できる
    else:
        editable = writable and not flags & _PDTF_ISINNATE and kind != KIND_OTHER
    choices = None
    if editable and kind in (KIND_INTEGER, KIND_CHOICE):
        choices = _get_choices(description, var_type)
        if choices is not None:
            kind = KIND_CHOICE
        elif kind == KIND_CHOICE:
            editable = False
    elif kind == KIND_CHOICE:
        kind = KIND_OTHER  # 変更できない真偽値は、表示用の文字列だけを使う
    if not has_value and not editable:
        return None  # 値がなく、変更もできない項目は表示しない

    value = None
    text = ""
    if has_value:
        try:
            text = _clean_text(description.FormatForDisplay(prop_value, 0))
        except pywintypes.com_error:
            text = ""
        try:
            value = prop_value.GetValue()
        except Exception:
            value = None
        if kind == KIND_DATE and isinstance(value, datetime.datetime):
            value = _to_local(value)
            if editable:
                text = value.strftime(DATE_FORMAT)
        elif kind == KIND_CHOICE:
            value = _find_choice(choices, description, prop_value)
        elif kind == KIND_TEXT_LIST and isinstance(value, (list, tuple)):
            value = list(value)
        if text == "" and value is not None:
            text = str(value)
    label = _clean_text(description.GetDisplayName()) or name
    return PropertyItem(name, label, group, kind, var_type, value, text, editable, choices)


def load(path):
    """(別スレッド)ファイルのプロパティ情報を読み込み、FileProperties を返す"""
    item = shell.SHCreateItemFromParsingName(path, None, shell.IID_IShellItem2)
    writable, write_error = _check_writable(item)
    descriptions = item.GetPropertyDescriptionList(pscon.PKEY_PropList_FullDetails, propsys.IID_IPropertyDescriptionList)
    store = item.GetPropertyStore(_GPS_DEFAULT, propsys.IID_IPropertyStore)
    items = []
    names = set()
    group = ""
    for i in range(descriptions.GetCount()):
        description = descriptions.GetAt(i, propsys.IID_IPropertyDescription)
        if description.GetTypeFlags(_PDTF_ALL) & _PDTF_ISGROUP:
            group = _clean_text(description.GetDisplayName())
            continue
        prop = _make_item(description, store, group, writable)
        if prop is None or prop.name in names:
            continue
        names.add(prop.name)
        items.append(prop)
    for name in FILE_TIME_NAMES:
        if name in names:
            continue
        # フォルダなど、一覧に作成日時・更新日時がない種類でも変更できるようにする
        key = propsys.PSGetPropertyKeyFromName(name)
        description = propsys.PSGetPropertyDescription(key, propsys.IID_IPropertyDescription)
        prop = _make_item(description, store, "", writable)
        if prop is not None:
            items.append(prop)
    return FileProperties(path, items, writable, write_error)


def parse_input(prop, text):
    """
    入力された文字列を、項目の値に変換する。空なら None（値を消す）。
    正しくなければ、理由を入れた ValueError を投げる。
    """
    text = text.strip()
    if prop.kind == KIND_TEXT_LIST:
        values = [v.strip() for v in text.split(";")]
        values = [v for v in values if v != ""]
        return values if values else None
    if text == "":
        if prop.name in FILE_TIME_NAMES:
            raise ValueError(_("%(name)sは空にできません。") % {"name": prop.label})
        return None
    if prop.kind == KIND_TEXT:
        return text
    if prop.kind == KIND_INTEGER:
        try:
            value = int(text)
        except ValueError:
            raise ValueError(_("整数を入力してください。"))
        minimum, maximum = _INTEGER_RANGES[prop.var_type]
        if not minimum <= value <= maximum:
            raise ValueError(_("%(min)d から %(max)d までの整数を入力してください。") % {"min": minimum, "max": maximum})
        return value
    if prop.kind == KIND_DECIMAL:
        try:
            return float(text)
        except ValueError:
            raise ValueError(_("数値を入力してください。"))
    if prop.kind == KIND_DATE:
        match = _DATE_INPUT_PATTERN.fullmatch(text)
        if match is None:
            raise ValueError(_("日時は「2024/01/31 13:45:00」の形で入力してください。"))
        try:
            value = datetime.datetime(*(int(v) for v in match.groups(default="0")))
            return value.astimezone()
        except ValueError:
            raise ValueError(_("存在しない日時です。"))
        except (OverflowError, OSError):
            # 1970年より前など、ローカル時刻に変換できない
            raise ValueError(_("この日時は指定できません。"))
    raise ValueError(_("この項目は変更できません。"))


def format_value(prop, value):
    """値を、一覧に表示する文字列にする"""
    if value is None:
        return ""
    if prop.kind == KIND_TEXT_LIST:
        return LIST_SEPARATOR.join(value)
    if prop.kind == KIND_DATE:
        return value.strftime(DATE_FORMAT)
    if prop.kind == KIND_CHOICE:
        for choice_value, label in prop.choices:
            if choice_value == value:
                return label
    if prop.kind == KIND_DECIMAL:
        return "%g" % value
    return str(value)


def _make_prop_variant(prop, value):
    """書き込む PROPVARIANT を作る"""
    if value is None:
        return propsys.PROPVARIANTType(None, pythoncom.VT_EMPTY)
    if prop.kind == KIND_DATE:
        return propsys.PROPVARIANTType(pywintypes.Time(value), pythoncom.VT_FILETIME)
    if prop.kind == KIND_DECIMAL:
        return propsys.PROPVARIANTType(float(value), prop.var_type)
    return propsys.PROPVARIANTType(value, prop.var_type)


def _set_file_times(path, created, modified):
    """ファイルやフォルダの作成日時と更新日時を変更する。None のものは変えない"""
    handle = win32file.CreateFile(
        path,
        _FILE_WRITE_ATTRIBUTES,
        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE | win32file.FILE_SHARE_DELETE,
        None,
        win32file.OPEN_EXISTING,
        win32file.FILE_FLAG_BACKUP_SEMANTICS,  # これがないとフォルダを開けない
        None)
    try:
        win32file.SetFileTime(
            handle,
            pywintypes.Time(created) if created is not None else None,
            None,
            pywintypes.Time(modified) if modified is not None else None,
            UTCTimes=True)
    finally:
        handle.Close()


def save(path, changes):
    """
    (別スレッド)変更を書き込む。changes は (PropertyItem, 新しい値) のリスト。
    プロパティを書き込むと更新日時が変わるので、作成日時・更新日時の変更は最後に行う。
    失敗したら例外を投げる。
    """
    file_times = {}
    properties = []
    for prop, value in changes:
        if prop.name in FILE_TIME_NAMES:
            file_times[prop.name] = value
        else:
            properties.append((prop, value))
    if properties:
        item = shell.SHCreateItemFromParsingName(path, None, shell.IID_IShellItem2)
        store = item.GetPropertyStore(_GPS_READWRITE, propsys.IID_IPropertyStore)
        for prop, value in properties:
            key = propsys.PSGetPropertyKeyFromName(prop.name)
            store.SetValue(key, _make_prop_variant(prop, value))
        store.Commit()
        del store
        log.info("saved %d properties of %s" % (len(properties), path))
    if file_times:
        _set_file_times(path, file_times.get(DATE_CREATED), file_times.get(DATE_MODIFIED))
        log.info("changed the file times of %s" % path)
