# -*- coding: utf-8 -*-
#Falcon default setting config
#Copyright (C) 2019 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

from FalconConfigParser import *


class DefaultSettings:
	"""
		このクラスには、キーの削除が許されない設定のデフォルト値を設定する。
		ここでの設定後にユーザが上書きできるが、ユーザ側ファイルに値がなければここでの値がそのまま利用される。
	"""

	def get():
		config = FalconConfigParser()
		config["general"]={
			"language": "ja-JP",
			"fileVersion": "100",
			"locale": "ja-JP"
		}
		config["speech"]={
			"reader": "AUTO",
			"fx_volume": 100
		}
		config["FileList"]={
			"sorting": 0,
			"descending": 0,
			"column_width_0" : "650",
			"column_width_1" : "150",
			"column_width_2" : "320",
			"column_width_3" : "70",
			"column_width_4" : "240"
		}
		config["GrepResultList"]={
			"sorting": 0,
			"descending": 0,
			"column_width_0" : 300,
			"column_width_1" : 80,
			"column_width_2" : 300,
			"column_width_3" : 70,
			"column_width_4" : 150,
			"column_width_5" : 320,
			"column_width_6" : 70,
			"column_width_7" : 240
		}
		config["DriveList"]={
			"sorting": 1,
			"descending": 0,
			"column_width_0": 250,
			"column_width_1": 120,
			"column_width_2": 150,
			"column_width_3": 150,
			"column_width_4": 480
		}
		config["SearchResultList"]={
			"sorting": 0,
			"descending": 0,
			"column_width_0" : "330",
			"column_width_1" : "150",
			"column_width_2" : "320",
			"column_width_3" : "320",
			"column_width_4" : "70",
			"column_width_5" : "240"
		}
		config["NetworkResourceList"]={
			"sorting" : "0",
			"descending" : "0",
			"column_width_0" : "620"
		}
		config["view"]={
			"font": "bold 'ＭＳ ゴシック' 22 windows-932",
			"colorMode":"normal",
			"header_title_length":20
		}
		config["mainView"]={
			"sizeX": "800",
			"sizeY": "600",
		}
		config["browse"]={
			"startPath": ""
		}
		config["search"]={
			"history_count": 20,
		}
		config["sounds"]={
			"startup" : "tip.ogg",
			"boundary" : "tip.ogg",
			"checked":"click.ogg",
			"check":"checked.ogg"
		}
		config["preview"]={
			"header_line_count": 10,
			"footer_line_count": 10,
			"audio_volume": 100
		}
		config["on_list_moved"]={
			"read_directory_level": True,
			"read_directory_name": True,
			"read_item_count": True
		}
		return config

initialValues={}
"""
	この辞書には、ユーザによるキーの削除が許されるが、初回起動時に組み込んでおきたい設定のデフォルト値を設定する。
	ここでの設定はユーザの環境に設定ファイルがなかった場合のみ適用され、初期値として保存される。
"""


initialValues["favorite_directories"]={
	"ドキュメント" : "%userprofile%\documents",
	"デスクトップ" : "%userprofile%\desktop"
}
initialValues["favorite_directories_shortcut"]={
	"ドキュメント" : "alt+1",
	"デスクトップ" : "alt+2"
}
initialValues["open_here"]={
	"Explorer" : "%windir%\explorer.exe \"%1\"",
	"コマンド プロンプト" : "%windir%\system32\cmd.exe /K cd /d  \"%1\"",
	"Windows Power Shell" : "%windir%\System32\WindowsPowerShell\\v1.0\powershell.exe -NoExit -command cd \'%1\'"
}
initialValues["open_here_shortcut"]={
	"Explorer" : "ctrl+e",
	"コマンド プロンプト" : "ctrl+shift+o",
	"Windows Power Shell" : "ctrl+shift+p"
}
initialValues["originalAssociation"]={
	"<default_file>": "C:\Program Files (x86)\KSD\MyEdit\MyEdit.exe",
	"<default_dir>": "falcon.exe"
}
