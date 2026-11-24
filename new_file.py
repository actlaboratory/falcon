# -*- coding: utf-8 -*-
# Falcon make new file
# Note: All comments except these top lines will be written in Japanese.

"""新しい空のファイルを作る処理（linux の touch 相当）"""

import errno
import os

import fileSystemManager


class FileType:
    """作成するファイルの種類"""

    def __init__(self, name: str, extension: str):
        # 画面に表示する名前
        self.name = name
        # ピリオドを含む拡張子。拡張子なしなら空文字列
        self.extension = extension

    def label(self):
        """選択肢として表示する文字列を返す"""
        if self.extension == "":
            return self.name
        return "%s (%s)" % (self.name, self.extension)


def get_file_types():
    """作成できるファイルの種類の一覧を返す。先頭が既定。"""
    return [
        FileType(_("テキスト文書"), ".txt"),
        FileType(_("Markdown 文書"), ".md"),
        FileType(_("CSV ファイル"), ".csv"),
        FileType(_("HTML 文書"), ".html"),
        FileType(_("JSON ファイル"), ".json"),
        FileType(_("拡張子なし"), ""),
    ]


def get_default_base_name():
    """名前が入力されなかったときに使う、拡張子を除くファイル名を返す"""
    return _("新しいファイル")


def make_name(name: str, file_type: FileType):
    """
    入力された名前から作成するファイル名を作る。
    拡張子が書かれていなければ、選ばれた種類の拡張子を付ける。
    """
    if os.path.splitext(name)[1] == "":
        return name + file_type.extension
    return name


def make_default_name(directory: str, file_type: FileType):
    """
    名前が入力されなかったときのファイル名を作る。
    同じ名前があれば「新しいファイル (2).txt」のように番号を付ける。
    """
    base = get_default_base_name()
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


def create(path: str):
    """
    空のファイルを作る。既存のファイルは上書きしない。
    失敗したときは、利用者に見せるエラーメッセージを返す。成功したら空文字列。
    """
    try:
        with open(path, "x"):
            pass
    except FileExistsError:
        return _("同じ名前のファイルまたはフォルダが既にあります。")
    except PermissionError:
        return _("アクセスが拒否されました。この場所にファイルを作成する権限がないか、読み取り専用の場所です。")
    except FileNotFoundError:
        return _("作成先のフォルダが見つかりません。")
    except OSError as e:
        if e.errno == errno.ENOSPC:
            return _("ディスクの空き容量が不足しています。")
        if e.errno == errno.EROFS:
            return _("読み取り専用の場所には作成できません。")
        detail = e.strerror if e.strerror else str(e)
        return _("ファイルを作成できませんでした。") + "\n" + detail
    return ""
