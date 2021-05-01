# キー押し下げ判定テスト
# 終了時はCtrl+Cを使うこと。

# 自分自身より上のディレクトリのものをimportするためのおまじない
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


import wx
import keymap
import time

app = wx.App()

while True:
    time.sleep(0.1)
    print("-----")
    for name, code in keymap.str2key.items():
        # マウス関連は利用不可
        if code <= 4:
            continue
        # カテゴリキーは取得不可、NumLockとCapsLockは押し下げ状態ではなく現在のON/OFFを返してしまうので
        if isinstance(
                code,
                wx.KeyCategoryFlags) or name == "NUMLOCK" or name == "SCROLL":
            continue
        if wx.GetKeyState(code):
            print(name)
