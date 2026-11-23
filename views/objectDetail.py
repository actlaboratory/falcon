# -*- coding: utf-8 -*-
# Falcon object detail view
# Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
# Note: All comments except these top lines will be written in Japanese.

import viewkit
import wx

import misc
import workerThreads
import workerThreadTasks

from viewkit.creator import viewCreator

# 計算中のフィールドを表す
CALCURATING = None


class ObjectDetailParameters:
    """
    ObjectDetailWindow に渡すパラメータ。
    items には (項目名, 内容) を表示順に追加する。内容に CALCURATING を指定した項目は、フォルダ容量の計算結果で埋められる。
    """

    def __init__(self):
        self.items = []
        self.dir_calc_path = None  # 容量を計算するフォルダのパス

    def add(self, title, content):
        self.items.append((title, content))


class ObjectDetailWindow(viewkit.SubWindow):
    """ファイルやドライブなどの詳細情報を表示するウィンドウ"""

    def __init__(self, parent, ctx, title, parameters: ObjectDetailParameters):
        super().__init__(parent, ctx, title, parameters)
        self.task = None
        self.calcurating_fields = []

        creator = self.creator.makeChild(viewCreator.FlexGridSizer, 20)
        for item_title, content in parameters.items:
            if content is not CALCURATING:
                creator.inputbox(item_title, x=400, default_value=str(content), style=wx.TE_READONLY)
            else:
                field, dummy = creator.inputbox(item_title, x=400, default_value=_("計算中"), style=wx.TE_READONLY)
                self.calcurating_fields.append(field)

        footer = self.creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
        footer.closebutton(_("ＯＫ"))

        if parameters.dir_calc_path is not None:
            param = {'lst': [(0, parameters.dir_calc_path)], 'callback': self._on_dir_calc_finished}
            self.task = workerThreads.RegisterTask(workerThreadTasks.DirCalc, param)

    def Destroy(self):
        if self.task:
            self.task.Cancel()
            self.task = None
        return super().Destroy()

    def _on_dir_calc_finished(self, results, task_state):
        self.task = None
        result = results[0][1]  # 2つ以上来ることはなく、パス文字列は不要
        if result[0] >= 0:
            values = (
                misc.ConvertBytesTo(result[0], misc.UNIT_AUTO, True),
                str(result[0]),
                _("ファイル数： %d サブディレクトリ数： %d") % (result[1], result[2]),
            )
        else:
            values = (_("不明"), _("不明"), _("不明"))
        for field, value in zip(self.calcurating_fields, values):
            field.SetValue(value)
