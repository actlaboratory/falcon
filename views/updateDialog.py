# -*- coding: utf-8 -*-
# update dialog
# Copyright (C) 2020 Hiroki Fujii <hfujii@hisystron.com>

import viewkit
import wx

import simpleDialog


class UpdateWindow(viewkit.SubWindow):
    """
    アップデートの案内とダウンロードの進行状況を表示するウィンドウ。
    parametersには update.update のインスタンスを指定する。ダウンロード中の進行状況表示のため、parameters.window にこのウィンドウが設定される。
    """

    def __init__(self, parent, ctx, title, parameters):
        super().__init__(parent, ctx, title, parameters)
        self.updater = parameters
        self.updater.window = self
        self.running = False
        info = self.updater.info

        creator = self.creator.makeChild(wx.VERTICAL, 5, style=wx.ALL, margin=20)
        if info["code"] == 200:
            self.info_static = creator.staticText(_("version %s にアップデートできます。") % (info["update_version"]))
            self.gauge, dummy = creator.gauge(_("進行状況"), x=600, style=wx.TOP, margin=5, text_layout=None)
            self.gauge.Disable()
            info_edit, dummy = creator.inputbox(_("version %s アップデート情報") % (info["update_version"]),
                                                default_value=info["update_description"], x=600, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_RAISED)
            info_edit.SetMinSize((600, 200))
            info_edit.SetMaxSize((600, 200))
            footer = creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT | wx.TOP, margin=20)
            self.start_button = footer.button(_("アップデート"), self._on_run_update)
        else:  # 緊急のお知らせ
            creator.inputbox(_("緊急のお知らせがあります。"), default_value=info["info_description"],
                             style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_RAISED)
            footer = creator.makeChild(wx.HORIZONTAL, 20, style=wx.ALIGN_RIGHT)
            footer.button(_("お知らせページへ"), self._on_open_browser)
        self.cancel_button = footer.cancelbutton(_("キャンセル"), self._on_cancel)

    def _on_cancel(self, event):
        if self.running:
            self.updater.exit()
            return
        self.end()

    def _on_open_browser(self, event):
        self.updater.open_site()
        self.end()

    def _on_run_update(self, event):
        self.running = True
        self.info_static.SetLabel(_("アップデートをダウンロード中..."))
        self.start_button.Disable()
        self.gauge.Enable()
        self.cancel_button.SetFocus()
        self.updater.start()

    def end(self):
        self.EndModal(wx.ID_OK)


def show_updater_not_found():
    simpleDialog.dialog(_("エラー"), _("updater.exeが見つかりませんでした。誤って削除したかなどをご確認ください。"))
