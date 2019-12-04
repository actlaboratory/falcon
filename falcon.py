# -*- coding: utf-8 -*-
#Falcon startup file
#run python fal.py to execute Falcon
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#See window.py for application entry point

import win32timezone#ダミー

def _(string): pass#dummy

from app import *
import constants
import globalVars

def main():
	global app
	app=falconAppMain()
	globalVars.app=app
	app.initialize()
	app.MainLoop()
	app.config.write()

#global schope
if __name__ == "__main__": main()