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

	# 存在しないキーで読み出しを試行した場合、自動的にそのキーが生成される
	def __getitem__(self,key):
		try:
			return FalconConfigSection(super().__getitem__(key))
		except KeyError as e:
			self.__setitem__(key,"")
			return ""
	#既に存在してもエラーにならないように変更
	def add_section(self,name):
		if not self.has_section(name):
			return super().add_section(name)

class FalconConfigSection(configparser.SectionProxy):
	def __init__(self,proxy):
		super().__init__(proxy._parser, proxy._name)

	def __getitem__(self,key):
		try:
			return super().__getitem__(key)
		except KeyError:
			self._parser[self._name][key]=""
			return ""

