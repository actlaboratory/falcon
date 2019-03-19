# -*- coding: utf-8 -*-
#Falcon startup file
#run python fal.py to execute Falcon
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#See window.py for application entry point
from app import *
import constants

def main():
	global app
	app=falconAppMain()
	app.initialize(constants.APP_NAME,constants.APP_WINDOW_SIZE_X,constants.APP_WINDOW_SIZE_Y)
	app.MainLoop()

#global schope
if __name__ == "__main__": main()