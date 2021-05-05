# -*- coding: utf-8 -*-
# Falcon key map management
# Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
# Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import browsableObjects
import keymapHandlerBase
import tabs
import views.menuBlocker

# KeyConfigDialogのための関数
str2key = keymapHandlerBase.str2key


def makeEntry(*pArgs, **kArgs):
    return keymapHandlerBase.makeEntry(*pArgs, *kArgs)


class KeymapHandler(keymapHandlerBase.KeymapHandlerBase):

    def __init__(self, dict=None, filter=None):
        super().__init__(dict, filter, permitConfrict=permitConfrict)


# 複数メニューに対するキーの割り当ての重複を許すか否かを調べる
# itemsには調べたいAcceleratorEntryのリストを入れる
def permitConfrict(items, log):
    tabTypeCondition = views.menuBlocker.tabTypeBlockList
    itemTypeCondition = views.menuBlocker.selectedItemTypeBlockList
    countCondition = views.menuBlocker.selectedItemCountBlockList

    flg = 0
    for i in [j.refName for j in items]:
        iFlag = 0
        # ファイルリストタブ
        if i not in tabTypeCondition[tabs.fileList.FileListTab]:
            if i not in itemTypeCondition[browsableObjects.File]:
                iFlag += 1
            if i not in itemTypeCondition[browsableObjects.Folder]:
                iFlag += 2
            if i not in countCondition[0]:
                iFlag += 4

        # ストリームリストタブ
        if i not in tabTypeCondition[tabs.streamList.StreamListTab]:
            iFlag += 8

        # ドライブリストタブ
        if i not in tabTypeCondition[tabs.driveList.DriveListTab]:
            if i not in itemTypeCondition[browsableObjects.Drive]:
                iFlag += 16

            if i not in itemTypeCondition[browsableObjects.NetworkResource]:
                iFlag += 32
            if i not in countCondition[0]:
                iFlag += 64

        # GrepResultTab
        if i not in tabTypeCondition[tabs.grepResult.GrepResultTab]:
            iFlag += 128

        # SearchResultTab
        if i not in tabTypeCondition[tabs.searchResult.SearchResultTab]:
            if i not in itemTypeCondition[browsableObjects.SearchedFile]:
                iFlag += 256
            if i not in itemTypeCondition[browsableObjects.SearchedFolder]:
                iFlag += 512
            if i not in countCondition[0]:
                iFlag += 1024

        if iFlag & flg == 0:
            flg += iFlag
        else:
            # 重複によるエラー
            log.warn("key confricted. " + i + " is confrict in " + str(items))
            return False
    log.debug("key not confricted. " + i + " is not confrict in " + str(items))
    return True


class KeyFilter(keymapHandlerBase.KeyFilterBase):
    pass
