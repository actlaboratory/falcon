# -*- coding: utf-8 -*-
#Falcon default setting config
#Copyright (C) 2019 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

from FalconConfigParser import *


class DefaultSettings:

	def get():
		config = FalconConfigParser()
		config["general"]={
			"language": "ja-JP",
			"fileVersion": "100",
			"locale": "EN-US"
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
		config["view"]={
			"font": "bold 'ＭＳ ゴシック' 22 windows-932",
			"colorMode":"normal"
		}
		config["mainView"]={
			"sizeX": "800",
			"sizeY": "600",
		}
		config["browse"]={
			"startPath": "%%HOMEDRIVE%%"
		}
		config["sounds"]={
			"startup" : "tip.ogg",
			"boundary" : "tip.ogg",
			"checked":"click.ogg",
			"check":"checked.ogg"
		}
		config["favorite_directories"]={
			"ドキュメント" : "%%%%userprofile%%%%\documents",
			"デスクトップ" : "%%%%userprofile%%%%\desktop"
		}
		config["favorite_directories_shortcut"]={
			"ドキュメント" : "alt+1",
			"デスクトップ" : "alt+2"
		}
		config["open_here"]={
			"Falcon(new window)" : "falcon.exe \"%%%%1\"",
			"Explorer" : "%%%%windir%%%%\explorer.exe \"%%%%1\"",
			"コマンド プロンプト" : "%%%%windir%%%%\system32\cmd.exe /K cd /d  \"%%%%1\"",
			"Windows Power Shell" : "%%%%windir%%%%\System32\WindowsPowerShell\\v1.0\powershell.exe -NoExit -command cd \'%%%%1\'"
		}
		config["open_here_shortcut"]={
			"Falcon(new window)" : "shift+return",
			"Explorer" : "ctrl+e",
			"コマンド プロンプト" : "ctrl+shift+o",
			"Windows Power Shell" : "ctrl+shift+p"
		}
		config["preview"]={
			"header_line_count": 10,
			"footer_line_count": 10
		}
		config['on_list_moved']={
			"read_directory_level": True,
			"read_directory_name": True,
			"read_item_count": True
		}
		return config

