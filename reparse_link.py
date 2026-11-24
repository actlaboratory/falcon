# -*- coding: utf-8 -*-
# Falcon symbolic link / junction utility
# Note: All comments except these top lines will be written in Japanese.

"""
シンボリックリンクとジャンクションの判別、リンク先の取得、リンク自体の移動。

どちらもリパースポイントなので、ファイルの属性だけでは区別できない。OneDrive のファイルなど、
リンクではないリパースポイントもあるため、リパースタグで判別する。
"""

import os
import stat
import uuid
import _winapi

import win32file
import winerror

KIND_SYMBOLIC_LINK = "symbolic_link"
KIND_JUNCTION = "junction"
# ジャンクションと同じリパースタグだが、フォルダではなくボリュームを指すもの
KIND_MOUNT_POINT = "mount_point"

_EXTENDED_PREFIX = "\\\\?\\"
_EXTENDED_UNC_PREFIX = "\\\\?\\UNC\\"
_VOLUME_PREFIX = "\\\\?\\volume{"


class LinkInfo:
    """リンクの情報。target は記録されているリンク先、is_directory はフォルダ用のリンクかどうか。"""

    def __init__(self, kind, target, is_directory):
        self.kind = kind
        self.target = target
        self.is_directory = is_directory


def _get_tag(path):
    """リパースタグを返す。リパースポイントでない場合や、調べられない場合は0を返す。"""
    try:
        return os.lstat(path).st_reparse_tag
    except (OSError, ValueError):
        return 0


def is_link(path):
    """パスがシンボリックリンクかジャンクション(マウントポイントを含む)かどうかを返す。リンク先はたどらない。"""
    return _get_tag(path) in (stat.IO_REPARSE_TAG_SYMLINK, stat.IO_REPARSE_TAG_MOUNT_POINT)


def is_directory_entry(path):
    """リンク先をたどらずに、パスがフォルダ(フォルダ用のリンクを含む)かどうかを返す。"""
    try:
        return bool(os.lstat(path).st_file_attributes & stat.FILE_ATTRIBUTE_DIRECTORY)
    except (OSError, ValueError):
        return False


def get_link(path):
    """リンクの情報を LinkInfo で返す。リンクでない場合は None を返す。リンク先を読み取れない場合は OSError。"""
    tag = _get_tag(path)
    if tag not in (stat.IO_REPARSE_TAG_SYMLINK, stat.IO_REPARSE_TAG_MOUNT_POINT):
        return None
    target = os.readlink(path)
    kind = KIND_SYMBOLIC_LINK
    if tag == stat.IO_REPARSE_TAG_MOUNT_POINT:
        kind = KIND_MOUNT_POINT if target.lower().startswith(_VOLUME_PREFIX) else KIND_JUNCTION
    if target.startswith(_EXTENDED_UNC_PREFIX):
        target = "\\\\" + target[len(_EXTENDED_UNC_PREFIX):]
    elif target.startswith(_EXTENDED_PREFIX) and kind != KIND_MOUNT_POINT:
        target = target[len(_EXTENDED_PREFIX):]
    return LinkInfo(kind, target, is_directory_entry(path))


def get_kind_name(kind):
    """リンクの種類の表示名を返す。"""
    names = {
        KIND_SYMBOLIC_LINK: _("シンボリックリンク"),
        KIND_JUNCTION: _("ジャンクション"),
        KIND_MOUNT_POINT: _("ボリュームのマウントポイント"),
    }
    return names[kind]


def get_absolute_target(path, link):
    """リンク先の絶対パスを返す。"""
    if link.kind == KIND_MOUNT_POINT:
        return link.target
    return os.path.normpath(os.path.join(os.path.dirname(path), link.target))


def move_link(path, destination, overwrite=False):
    """リンク先の中身には触れず、リンク自体を移動する。失敗した場合は win32file.error か OSError。"""
    if not overwrite and os.path.lexists(destination):
        raise win32file.error(winerror.ERROR_ALREADY_EXISTS, "move_link", _("すでに存在します。"))
    flags = win32file.MOVEFILE_REPLACE_EXISTING if overwrite else 0
    try:
        # MOVEFILE_COPY_ALLOWED を付けると、別のドライブへの移動でリンク先の中身がコピーされることがある
        win32file.MoveFileEx(path, destination, flags)
        return
    except win32file.error as err:
        if err.winerror != winerror.ERROR_NOT_SAME_DEVICE:
            raise
    # 別のドライブへは名前の変更だけでは移動できないので、移動先に同じリンクを作ってから元のリンクを消す
    temporary = os.path.join(os.path.dirname(destination), "falcon_%s.tmp" % uuid.uuid4().hex)
    link = get_link(path)
    _create_link(link, temporary)
    try:
        win32file.MoveFileEx(temporary, destination, flags)
    except win32file.error:
        _remove_link(temporary, link.is_directory)
        raise
    try:
        _remove_link(path, link.is_directory)
    except win32file.error:
        # 元のリンクを消せなかった。上書きした移動先は元に戻せないので、移動先のリンクは上書きでないときだけ消す
        if not overwrite:
            _remove_link(destination, link.is_directory)
        raise


def _create_link(link, path):
    """同じ内容のリンクを作る。"""
    if link.kind == KIND_SYMBOLIC_LINK:
        os.symlink(link.target, path, target_is_directory=link.is_directory)
        return
    if link.kind == KIND_MOUNT_POINT:
        raise win32file.error(winerror.ERROR_NOT_SUPPORTED, "move_link", _("マウントポイントを別のドライブへ移動することはできません。"))
    try:
        _winapi.CreateJunction(link.target, path)
    except OSError:
        # 途中で失敗すると、空のフォルダが残ることがある
        if os.path.isdir(path):
            os.rmdir(path)
        raise


def _remove_link(path, is_directory):
    """リンク先の中身には触れず、リンクを削除する。"""
    if is_directory:
        win32file.RemoveDirectory(path, None)
    else:
        win32file.DeleteFile(path)
