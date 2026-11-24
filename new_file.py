# -*- coding: utf-8 -*-
# Falcon make new file
# Note: All comments except these top lines will be written in Japanese.

"""
新しいファイルを作る処理。
エクスプローラーの「新規作成」に登録された種類（ShellNew）と、falcon が持つ空ファイルの種類から選んで作る。
"""

import errno
import logging
import os

import win32api
import win32con

import fileSystemManager
import shell_new

log = logging.getLogger("falcon.newFile")


class FileType:
    """作成するファイルの種類"""

    def __init__(self, name: str, extension: str, default_base_name: str,
                 method: str = shell_new.METHOD_NULL_FILE, value=None):
        # 画面に表示する名前
        self.name = name
        # ピリオドを含む拡張子。拡張子なしなら空文字列
        self.extension = extension
        # 名前が入力されなかったときのファイル名（拡張子を除く）
        self.default_base_name = default_base_name
        # 作り方（shell_new.METHOD_ のいずれか）と、その値
        self.method = method
        self.value = value

    def label(self):
        """選択肢として表示する文字列を返す"""
        if self.extension == "":
            return self.name
        return "%s (%s)" % (self.name, self.extension)


class NewFileRequest:
    """作成するファイルの名前と種類"""

    def __init__(self, name: str, file_type: FileType):
        self.name = name
        self.file_type = file_type


def _new_name(type_name: str):
    """種類の名前から、既定のファイル名を作る"""
    return _("新規 %(type)s") % {"type": type_name}


def _get_builtin_types():
    """falcon が持つ、空のファイルを作る種類の一覧を返す"""
    types = []
    for name, extension in (
        (_("テキスト文書"), ".txt"),
        (_("Markdown 文書"), ".md"),
        (_("CSV ファイル"), ".csv"),
        (_("HTML 文書"), ".html"),
        (_("JSON ファイル"), ".json"),
    ):
        types.append(FileType(name, extension, _new_name(name)))
    types.append(FileType(_("拡張子なし"), "", _("新しいファイル")))
    return types


def get_file_types():
    """
    作成できるファイルの種類の一覧を返す。
    ShellNew に登録された種類を先に並べ、そのあとに ShellNew にない falcon の種類を並べる。
    """
    try:
        entries = shell_new.get_entries()
    except Exception:
        log.exception("cannot read ShellNew")
        entries = []
    types = []
    for entry in entries:
        default_base_name = entry.item_name if entry.item_name else _new_name(entry.type_name)
        types.append(FileType(entry.type_name, entry.extension, default_base_name, entry.method, entry.value))
    extensions = {t.extension.lower() for t in types}
    for t in _get_builtin_types():
        if t.extension.lower() not in extensions:
            types.append(t)
    return types


def get_default_index(file_types: list):
    """最初に選んでおく種類（テキスト文書）の位置を返す"""
    for i, t in enumerate(file_types):
        if t.extension.lower() == ".txt":
            return i
    return 0


def make_name(name: str, file_type: FileType):
    """
    入力された名前から作成するファイル名を作る。
    空のファイルを作る種類なら、拡張子が書かれていないときだけ、選ばれた種類の拡張子を付ける。
    ひな形のコピーなど中身が決まっている種類なら、名前がその種類の拡張子で終わっていなければ付ける。
    """
    extension = file_type.extension
    if extension == "":
        return name
    if file_type.method != shell_new.METHOD_NULL_FILE:
        if name.lower().endswith(extension.lower()):
            return name
        return name + extension
    # 「.gitignore」のようにピリオドで始まる名前は、それ全体が名前なので拡張子を付けない
    if os.path.splitext(name)[1] == "" and not name.startswith("."):
        return name + extension
    return name


def make_default_name(directory: str, file_type: FileType):
    """
    名前が入力されなかったときのファイル名を作る。
    同じ名前があれば「新規 テキスト文書 (2).txt」のように番号を付ける。
    """
    base = file_type.default_base_name
    name = base + file_type.extension
    number = 2
    while os.path.lexists(os.path.join(directory, name)):
        name = "%s (%d)%s" % (base, number, file_type.extension)
        number += 1
    return name


def validate(directory: str, name: str):
    """作成するファイル名に問題があればその内容を返す。問題なければ空文字列。"""
    if name.strip() == "":
        return _("ファイル名を入力してください。")
    path = os.path.join(directory, name)
    error = fileSystemManager.ValidationObjectName(path, fileSystemManager.pathTypes.FILE, name)
    if error != "":
        return error
    if os.path.lexists(path):
        return _("同じ名前のファイルまたはフォルダが既にあります。")
    return ""


def create(path: str, file_type: FileType):
    """
    ファイルを作る。既存のファイルは上書きしない。
    失敗したときは、利用者に見せるエラーメッセージを返す。成功したら空文字列。
    METHOD_COMMAND の場合はプログラムを起動するだけで、ファイルは起動したプログラムが作る。
    """
    if file_type.method == shell_new.METHOD_COMMAND:
        return _run_command(path, file_type.value)
    try:
        content = _get_content(file_type)
    except OSError as e:
        log.warning("cannot read template %s: %s" % (file_type.value, e))
        return _("ひな形のファイルを読み込めませんでした。") + "\n" + str(file_type.value)
    created = False
    try:
        with open(path, "xb") as f:
            created = True
            f.write(content)
    except FileExistsError:
        return _("同じ名前のファイルまたはフォルダが既にあります。")
    except PermissionError:
        return _("アクセスが拒否されました。この場所にファイルを作成する権限がないか、読み取り専用の場所です。")
    except FileNotFoundError:
        return _("作成先のフォルダが見つかりません。")
    except OSError as e:
        # 書き込みの途中で失敗したら、作りかけのファイルを消す。自分で作ったファイル以外は消さない
        if created:
            _remove_incomplete(path)
        if e.errno == errno.ENOSPC:
            return _("ディスクの空き容量が不足しています。")
        if e.errno == errno.EROFS:
            return _("読み取り専用の場所には作成できません。")
        detail = e.strerror if e.strerror else str(e)
        return _("ファイルを作成できませんでした。") + "\n" + detail
    return ""


def _get_content(file_type: FileType):
    """作成するファイルの中身を返す。ひな形が読めなければ OSError。"""
    if file_type.method == shell_new.METHOD_DATA:
        return file_type.value
    if file_type.method == shell_new.METHOD_TEMPLATE:
        with open(file_type.value, "rb") as f:
            return f.read()
    return b""


def _remove_incomplete(path: str):
    """書き込みの途中で失敗したファイルを消す"""
    try:
        os.remove(path)
    except OSError:
        pass


def split_command(command: str):
    """コマンドラインを、実行するプログラムと引数に分ける"""
    command = command.strip()
    if command.startswith("\""):
        end = command.find("\"", 1)
        if end < 0:
            return command[1:], ""
        return command[1:end], command[end + 1:].strip()
    parts = command.split(" ", 1)
    return parts[0], parts[1].strip() if len(parts) > 1 else ""


def _run_command(path: str, command: str):
    """ShellNew の Command を実行する。%1 は作成するファイルのパスに置き換える。"""
    program, arguments = split_command(command)
    arguments = arguments.replace("%1", path)
    log.info("run ShellNew command: %s %s" % (program, arguments))
    try:
        win32api.ShellExecute(0, None, program, arguments, os.path.dirname(path), win32con.SW_SHOWNORMAL)
    except win32api.error as e:
        return _("プログラムを起動できませんでした。") + "\n" + program + "\n" + str(e.strerror)
    return ""
