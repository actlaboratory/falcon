# -*- coding: utf-8 -*-
#FalconConfigManager
#Copyright (C) 2019 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 



import os
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
		if os.path.exists(fileName):
			self.log.info("read configFile:"+fileName)
			try:
				return super().read(fileName)
			except configparser.ParsingError:
				return {}
		else:
			self.log.warning("configFile not found.")
			return self

	def write(self):
		self.log.info("write configFile:"+self.fileName)
		with open(self.fileName,"w") as f: return super().write(f)

	def __getitem__(self,key):
		try:
			return FalconConfigSection(super().__getitem__(key))
		except KeyError as e:
			self.log.debug("create new section:"+key)
			self.add_section(key)
			return self.__getitem__(key)

	def getboolean(self,section,key,default=True):
		if type(default)!=bool:
			raise ValueError("default value must be boolean")
		try:
			return super().getboolean(section,key)
		except ValueError:
			self.log.debug("value is not boolean.  return default "+str(default)+" at section "+section+", key "+key)
			self[section][key]=str(default)
			return default
		except configparser.NoOptionError as e:
			self.log.debug("add new boolval "+str(default)+" at section "+section+", key "+key)
			self[section][key]=default
			return default
		except configparser.NoSectionError as e:
			self.log.debug("add new section and boolval "+str(default)+" at section "+section+", key "+key)
			self.add_section(section)
			self.__getitem__(section).__setitem__(key,default)
			return default

	def getint(self,section,key,default=0,min=None,max=None):
		if type(default)!=int:
			raise ValueError("default value must be int")
		try:
			ret = super().getint(section,key)
			if (min!=None and ret<min) or (max!=None and ret>max):
				self.log.debug("intvalue "+str(ret)+" out of range.  at section "+section+", key "+key)
				self[section][key]=str(default)
				return int(default)
			return ret
		except configparser.NoOptionError as e:
			self.log.debug("add new intval "+str(default)+" at section "+section+", key "+key)
			self[section][key]=str(default)
			return int(default)
		except configparser.NoSectionError as e:
			self.log.debug("add new section and intval "+str(default)+" at section "+section+", key "+key)
			self.add_section(section)
			self.__getitem__(section).__setitem__(key,str(default))
			return int(default)

	def getstring(self,section,key,default="",selection=None,*, raw=False, vars=None,fallback=None):
		if type(selection) not in (set,tuple):
			raise TypeError("selection must be set or tuple")
		ret=self.__getitem__(section)[key]
		if ret=="" and default!="":
			self.log.debug("add default value.  at section "+section+", key "+key)
			self[section][key]=default
			ret=default

		if selection==None:return ret
		if ret not in selection:
			self.log.debug("value "+ret+" not in selection.  at section "+section+", key "+key)
			self[section][key]=default
			ret=default
		return ret

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
