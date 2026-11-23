# versionDialog
# Copyright (C) 2020 Hiroki Fujii <hfujii@hisystron.com>

import viewkit
import wx

import constants
import update


class VersionWindow(viewkit.SubWindow):
    """バージョン情報を表示するウィンドウ"""

    def __init__(self, parent, ctx, title, parameters=None):
        super().__init__(parent, ctx, title, parameters)
        text_list = []
        text_list.append(str(constants.APP_FULL_NAME) + " (" + constants.APP_NAME + ")")
        text_list.append(_("ソフトウェアバージョン") + ": " + str(constants.APP_VERSION))
        try:
            text_list.append(_("アップデータバージョン") + ": " + update.getUpdaterVersion()[1])
        except BaseException:
            pass
        text_list.append(_("viewkit バージョン") + ": " + viewkit.__version__)
        text_list.append(_("ライセンス") + ": " + constants.APP_LICENSE)
        text_list.append(_("開発元") + ": %s - %s" % (constants.APP_DEVELOPERS, constants.APP_DEVELOPERS_URL))
        text_list.append(_("ソフトウェア詳細情報") + ": " + constants.APP_DETAILS_URL)
        text_list.append("")
        text_list.append(_("ライセンス/著作権情報については、同梱の license.txt を参照してください。"))
        text_list.append("")
        text_list.append(constants.APP_COPYRIGHT_MESSAGE)

        creator = self.creator.makeChild(wx.VERTICAL, 10, style=wx.ALL, margin=20)
        self.info, dummy = creator.inputbox("", default_value="\r\n".join(text_list), style=wx.TE_MULTILINE |
                                            wx.TE_READONLY | wx.TE_NO_VSCROLL | wx.BORDER_RAISED, sizer_flag=wx.EXPAND, x=750, text_layout=None)
        font = self.info.GetFont()
        font.SetPointSize(int(font.GetPointSize() * (2 / 3)))
        self.info.SetFont(font)
        self.info.SetMinSize(wx.Size(750, 240))

        # フッター
        footer = self.creator.makeChild(style=wx.ALIGN_RIGHT | wx.ALL, margin=20)
        close_button = footer.closebutton(_("閉じる"))
        close_button.SetDefault()
