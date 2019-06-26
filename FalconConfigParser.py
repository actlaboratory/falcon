# -*- coding: utf-8 -*-
#FalconConfigManager
#Copyright (C) 2019 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 




import configparser


class FalconConfigParser(configparser.ConfigParser):


	fileName=""

	def read(self,fileName):
		self.fileName=fileName
		return super().read(fileName)


	def write(self):
		with open(self.fileName,"w") as f: return super().write(f)

