# -*- coding: utf-8 -*-
#Falcon startup file
#run python fal.py to execute Falcon
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#See window.py for application entry point

import os
import sys
#カレントディレクトリを設定
if hasattr(sys,"frozen"): os.chdir(os.path.dirname(sys.executable))
else: os.chdir(os.path.abspath(os.path.dirname(__file__)))

import win32timezone#ダミー

def _(string): pass#dummy

#dllをカレントディレクトリから読み込むように設定

os.add_dll_directory(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import traceback
import app as application
import constants
import globalVars

def main():
	if os.path.exists("errorLog.txt"): os.remove("errorLog.txt")
	global app
	app=application.falconAppMain()
	globalVars.app=app
	app.initialize()
	app.MainLoop()
	app.config.write()

def exchandler(type, exc, tb):
	msg=traceback.format_exception(type, exc, tb)
	print("".join(msg))
	f=open("errorLog.txt", "a")
	f.writelines(msg)
	f.close()
	if globalVars.app: globalVars.app.PlayErrorSound()

#global schope
sys.excepthook=exchandler

if __name__ == "__main__": main()
