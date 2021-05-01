# -*- coding: utf-8 -*-
# Falcon file operation handler confirm elements
# Copyright (C) 2019-2020 Yukio Nozawa <personal@nyanchangames.com>
# Note: All comments except these top lines will be written in Japanese.
"""ファイルオペレーションの結果、ユーザーに対して確認が必要になった項目を管理します。"""


class ConfirmElement(object):
    def __init__(self, elem, msg_number, msg_string):
        self.elem = elem
        self.msg_number = msg_number
        self.msg_string = msg_string
        self.response = None

    def GetElement(self):
        return self.elem

    def GetMessageNumber(self):
        return self.msg_number

    def GetMessageString(self):
        return self.msg_string

    def Respond(self, res):
        self.response = res

    def GetResponse(self):
        return self.response

    def IsResponded(self):
        return self.Response is not None

    def __str__(self):
        return "[%s] %s (%s)" % (self.msg_number, self.msg_str, self.elem)


class ConfirmationManager(object):
    def __init__(self):
        self.confirmations = []

    def Append(self, elem):
        self.confirmations.append(elem)

    def Remove(self, elem):
        self.confirmations.Remove(elem)

    def __len__(self):
        return len(self.confirmations)

    def GetAt(self, index):
        return self.confirmations[index]

    def Iterate(self):
        for elem in self.confirmations:
            yield elem

    def IterateNotResponded(self):
        for elem in self.confirmations:
            if not elem.IsResponded():
                yield elem

    def IterateResponded(self):
        for elem in self.confirmations:
            if elem.IsResponded():
                yield elem

    def IterateWithFilter(self, number=None):
        for elem in self.confirmations:
            ok = True
            if number is not None and elem.msg_number != number:
                ok = False
            if ok:
                yield elem
        # end for
    # end IterateWithFilter

    def RespondAll(self, elem, response):
        """指定したものより先にある、同じエラー番号の項目を、全て response として返答する。"""
        # インデックス番号を見つける
        i = 0
        for e in self.confirmations:
            if e is elem:
                break
            i += 1
        # end インデックス番号を見つける
        msg_number = elem.GetMessageNumber()
        for i2 in range(i, len(self.confirmations)):
            if self.confirmations[i2].GetMessageNumber() == msg_number:
                self.confirmations[i2].Respond(response)
        # end 全部応答
    # end RespondAll
