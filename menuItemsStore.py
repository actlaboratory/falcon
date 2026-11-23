# -*- coding: utf-8 -*-
# Filer menu items store
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.

# wx のメニューのrefを一括管理してくれる便利な人
# viewkit の RefStore と同じインターフェース(getRef/getIdentifier)を持ち、メインウィンドウのrefStoreとしても使われる。

import constants


class _MenuItemsStore(object):
    """このクラスは、外からインスタンス化してはいけません。"""

    def __init__(self):
        self.refs = {}
        self.nextID = constants.MENU_ID_FROM_FALCON

    def getRef(self, identifier):
        """識別子に対応するrefを返す。なかったら作ってから返す。識別子の大文字小文字は区別しない。"""
        identifier = identifier.upper()
        if identifier not in self.refs:
            self.refs[identifier] = self.nextID
            self.nextID += 1
        return self.refs[identifier]

    def getIdentifier(self, ref):
        """refに対応する識別子を返す。なければNoneを返す。"""
        for identifier, r in self.refs.items():
            if r == ref:
                return identifier
        return None


_store = _MenuItemsStore()


def getRef(identifier):
    """文字列から、対応するメニューのrefを取得する。なかったら、作ってから帰す。"""
    return _store.getRef(identifier)


def getIdentifier(ref):
    """refから、対応するメニューの識別子を取得する。なければNoneを返す。"""
    return _store.getIdentifier(ref)


def getStore():
    """viewkit の RefStore として利用するためのインスタンスを返す。"""
    return _store
