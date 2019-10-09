# -*- coding: utf-8 -*-
#FalconConfigManager
#Copyright (C) 2019 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 




import configparser
import logging
from logging import getLogger, FileHandler, Formatter


class FalconConfigParser(configparser.ConfigParser):


	def __init__(self):
		super().__init__()
		self.identifier="falconConfigParser"
		self.log=getLogger("falcon.%s" % self.identifier)
		self.log.debug("Create config instance")

	def read(self,fileName):
		self.fileName=fileName
		self.log.info("read configFile:"+fileName)
		return super().read(fileName)


	def write(self):
		self.log.info("write configFile:"+self.fileName)
		with open(self.fileName,"w") as f: return super().write(f)

	# 存在しないキーで読み出しを試行した場合、自動的にそのキーが生成される
	def __getitem__(self,key):
		try:
			return FalconConfigSection(super().__getitem__(key))
		except KeyError as e:
			self.log.debug("create new section:"+key)
			self.add_section(key)
			return self.__getitem__(key)

	#既に存在してもエラーにならないように変更
	def getint(self,section,key,default=0):
		try:
			return super().getint(section,key)
		except configparser.NoOptionError as e:
			self.log.debug("add new intval "+str(default)+" at section "+section+", key "+key)
			self[section][key]=str(default)
			return int(default)
		except configparser.NoSectionError as e:
			self.log.debug("add new section and intval "+str(default)+" at section "+section+", key "+key)
			self.add_section(section)
			self.__getitem__(section).__setitem__(key,str(default))
			return int(default)

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

	def __setitem__(self,key,_value):
		if (isinstance(_value,int)):
			value=str(_value)
		else:
			value=_value

		return super().__setitem__(key,value)
