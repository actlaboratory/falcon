# -*- coding: utf-8 -*-
#Falcon default setting config
#Copyright (C) 2019 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

from configparser import *

class DefaultSettings:

	def get():
		config = ConfigParser()
		config["general"]={
			"language": "ja-JP",
			}
		config["MainView"]={
			"sizeX": "800",
			"sizeY": "600",
			}
		config["Browse"]={
			"startPath": "%%USERPROFILE%%\\documents"
			}
		return config
