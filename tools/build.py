# -*- coding: utf-8 -*-
#app build tool
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
import os
import sys
import subprocess
import shutil
import distutils.dir_util

def runcmd(cmd):
	proc=subprocess.call(cmd.split(), shell=True)
	#proc.communicate()

appveyor=False

if len(sys.argv)==2 and sys.argv[1]=="--appveyor":
	appveyor=True

print("Starting build (appveyor mode=%s)" % appveyor)

pyinstaller_path="pyinstaller.exe" if appveyor is False else "%PYTHON%\\Scripts\\pyinstaller.exe"

print("pyinstaller_path=%s" % pyinstaller_path)
if not os.path.exists("locale"):
	print("Error: no locale folder found. Your working directory must be the root of the falcon project. You shouldn't cd to tools and run this script.")

if os.path.isdir("dist\\falcon"):
	print("Clearling previous build...")
	shutil.rmtree("dist\\")
	shutil.rmtree("build\\")

print("Building Falcon...")
runcmd("%s --windowed --log-level=ERROR falcon.py" % pyinstaller_path)
shutil.copyfile("xd2txlib.dll","dist\\falcon\\xd2txlib.dll")
shutil.copytree("locale\\","dist\\falcon\\locale", ignore=shutil.ignore_patterns("*.po", "*.pot", "*.po~"))
shutil.copytree("fx\\","dist\\falcon\\fx")
if os.path.exists("dist\\falcon\\bass"): os.rename("dist\\falcon\\bass","dist\\falcon\\bass.dll")
print("Building file operator...")
runcmd("%s --windowed --log-level=ERROR fileop.py" % pyinstaller_path)
distutils.dir_util.copy_tree("dist\\fileop","dist\\falcon")
shutil.rmtree("dist\\fileop")
print("Compressing into package...")
shutil.make_archive('falcon','zip','dist\\falcon')
print("Done!")
