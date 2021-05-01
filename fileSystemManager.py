# -*- coding: utf-8 -*-
# Falcon file system objects
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import win32api
import re
import os
from enum import Enum


def GetFileSystemObject(letter):
    """
    ドライブレターから、そのドライブのファイルシステムを取得する。

    :param letter: ドライブレター1文字。
    :type letter: str
    :rtype: FileSystemBase
    """
    name = win32api.GetVolumeInformation("%s:\\" % (letter[0]))[4]
    try:
        cls = globals()[name]
    except KeyError:
        return None
    # end keyError
    return cls()


def ValidationObjectName(path, pathType, path2=""):
    """
            ファイルやディレクトリの名前pathに何らかの問題があればその内容を返す
            pathは原則フルパス
            typeはpathTypeから１つを指定
            ボリュームラベル変更などでpathがドライブ名を含まない場合、path2でドライブ名を指定
            その他の場合、path2にはオブジェクト名のみを記載(フルパスからベースディレクトリを除いた部分)
    """
    # path2には\を含められない
    if '\\' in path2:
        return _("「\\」 は、ファイルやディレクトリの名前として使用できない記号です。")
    elif '/' in path2:
        return _("「/」 は、ファイルやディレクトリの名前として使用できない記号です。")
    s = os.path.split(path)[1]

    # 使用できない文字の確認
    ngString = []
    for c in ("\\", "/", ":", "*", "?", "\"", "<", ">", "|"):
        if c in s:
            ngString.append(c)
    if ngString:
        tmp = ""
        for c in ngString:
            if tmp != "":
                tmp += " ・ "
            tmp += "「" + c + "」"
        tmp += _("は、ファイルやディレクトリの名前として使用できない記号です。")
        return tmp

    # 使用できない特別な名前
    for i in ("CON", "AUX", "PRN", "NUL"):
        if re.sub("^(" + i + "$)|(" + i + "\\..*)", r"", s.upper()) == "":
            return _("この文字列は、Windowsによって予約された特別な名前のため、ファイルやディレクトリの名前として使用できません。")
    for i in ("COM", "LPT"):
        if re.sub(
            "^(" + i + "[1-9]$)|(" + i + "[1-9]\\..*)",
            r"",
                s.upper()) == "":
            return _("この文字列は、Windowsによって予約された特別な名前のため、ファイルやディレクトリの名前として使用できません。")

    # 末尾が.と半角スペースでないことの確認
    if re.sub("(.*\\.$)|(.* $)", r"", s) == "":
        return _("名前の最後を半角の.(ピリオド)または半角スペースとすることはできません。")

    # パス長の確認
    if pathType == pathTypes.VOLUME_LABEL:
        drive = GetFileSystemObject(path2)
        # TODO
    else:
        drive = GetFileSystemObject(os.path.splitdrive(path)[0])
        if len(s) > drive.MAX_PATH_LENGTH:
            return _("このドライブでは、以下の文字数を超えない名前を付ける必要があります。\n\n制限文字数:" +
                     str(drive.MAX_PATH_LENGTH))
        if pathType == pathTypes.DIRECTORY:
            if len(path) > drive.MAX_DIRECTORY_PATH_LENGTH:
                return _("このドライブでは、ディレクトリ名のフルパスが以下の文字数を超えないように名前を付ける必要があります。\n\n制限文字数:" +
                         str(drive.MAX_DIRECTORY_PATH_LENGTH))
        elif pathType == pathTypes.FILE:
            if len(path) > drive.MAX_FULLPATH_LENGTH:
                return _("このドライブでは、ファイル名のフルパスが以下の文字数を超えないように名前を付ける必要があります。\n\n制限文字数:" +
                         str(drive.MAX_FULLPATH_LENGTH))
    # 問題なし
    return ""


class pathTypes(Enum):
    DIRECTORY = 0
    FILE = 1
    VOLUME_LABEL = 2


class limitTypes(Enum):
    CHAR = 0
    BYTE = 1


class FileSystemBase(object):
    def __init__(self):
        self.canMakeHardLink = True
        self.canMakeSymbolicLink = True

    MAX_PATH_LENGTH = 255
    MAX_DIRECTORY_PATH_LENGTH = 247
    MAX_FULLPATH_LENGTH = 259


class NTFS(FileSystemBase):
    def __str__(self):
        return "NTFS"

    MAX_VOLUME_LABEL_TYPE = limitTypes.CHAR
    MAX_VOLUME_LABEL_LENGTH = 32


class FAT(FileSystemBase):
    def __str__(self):
        return "FAT"

    MAX_VOLUME_LABEL_TYPE = limitTypes.BYTE
    MAX_VOLUME_LABEL_LENGTH = 11


class FAT32(FileSystemBase):
    def __str__(self):
        return "FAT32"

    MAX_VOLUME_LABEL_TYPE = limitTypes.BYTE
    MAX_VOLUME_LABEL_LENGTH = 11


class exFAT(FileSystemBase):
    def __str__(self):
        return "exFAT"

    MAX_VOLUME_LABEL_TYPE = limitTypes.BYTE
    MAX_VOLUME_LABEL_LENGTH = 11


class UDF(FileSystemBase):
    def __str__(self):
        return "UDF"

    MAX_VOLUME_LABEL_TYPE = limitTypes.CHAR
    MAX_VOLUME_LABEL_LENGTH = 32


class CDFS(FileSystemBase):
    def __str__(self):
        return "CDFS"
