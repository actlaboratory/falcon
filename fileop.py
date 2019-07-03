# -*- coding: utf-8 -*-
#Falcon external file operator
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 
import logging
from logging import getLogger, FileHandler, Formatter
import sys
import traceback
import fileOperator

def main():
	global log
	log.info("Starting Falcon external file operation.")
	if len(sys.argv)<2:
		log.error("No parameter specified.")
		sys.exit(0)
	#end error
	file=sys.argv[1]
	log.info("given:%s" % file)
	o=fileOperator.FileOperator(file,elevated=True)
	o.Execute()
	log.info("End")
	sys.exit(0)

def Onerror(type, exc, tb):
	global log
	log.error("crashed!")
	for elem in traceback.format_exception(type, exc, tb):
		log.error(elem.strip())
	#end writing
	sys.exit(0)

#global schope
if __name__ == "__main__":
	hLogHandler=FileHandler("falconFOP.log", mode="w", encoding="UTF-8")
	hLogHandler.setLevel(logging.DEBUG)
	hLogFormatter=Formatter("%(name)s - %(levelname)s - %(message)s (%(asctime)s)")
	hLogHandler.setFormatter(hLogFormatter)
	log=getLogger("falcon")
	log.setLevel(logging.DEBUG)
	log.addHandler(hLogHandler)
	sys.excepthook=Onerror
	main()