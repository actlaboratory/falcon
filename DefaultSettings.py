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
			"boundary" : "tip.ogg"
		}

		return config

