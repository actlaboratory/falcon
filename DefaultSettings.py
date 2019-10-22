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
		}
		config["fileList"]={
			"sorting": 0,
			"descending": 0
		}
		config["driveList"]={
			"sorting": 1,
			"descending": 0
		}
		config["view"]={
			"font": "bold 'ＭＳ ゴシック' 22 windows-932"
		}
		config["mainView"]={
			"sizeX": "800",
			"sizeY": "600",
		}
		config["wxTestView"]={
			"sizeX": "800",
			"sizeY": "600",
		}
		config["browse"]={
			"startPath": "%%HOMEDRIVE%%"
		}
		config["MainListTab"]={
			"column_width_0" : "750",
			"column_width_1" : "150",
			"column_width_2" : "320",
			"column_width_3" : "70",
			"column_width_4" : "240"
		}

		config["changeAttributeDialog"]={
			"sizex" : 640,
			"sizey" : 360,
			"positionx" : -1,
			"positiony" : -1
		}
		config["sounds"]={
			"startup" : "tip.ogg",
			"boundary" : "tip.ogg"
		}

		return config

