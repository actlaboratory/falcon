# -*- coding: utf-8 -*-
#app build tool
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
import os
import sys
import subprocess
import shutil
import distutils.dir_util

def runcmd(cmd):
	proc=subprocess.Popen(cmd.split(), shell=True, stdout=1, stderr=2)
	proc.communicate()

if not os.path.exists("locale"):
	print("Error: no locale folder found. Your working directory must be the root of the falcon project. You shouldn't cd to tools and run this script.")

if os.path.isdir("dist\\falcon"):
	print("Clearling previous build...")
	shutil.rmtree("dist\\")
	shutil.rmtree("build\\")

print("Building Falcon...")
runcmd("pyinstaller --log-level=ERROR falcon.py")
shutil.copytree("locale\\","dist\\falcon\\locale", ignore=shutil.ignore_patterns("*.po", "*.pot", "*.po~"))
shutil.copytree("fx\\","dist\\falcon\\fx")
if os.path.exists("dist\\falcon\\bass"): os.rename("dist\\falcon\\bass","dist\\falcon\\bass.dll")
print("Building file operator...")
runcmd("pyinstaller --windowed --log-level=ERROR fileop.py")
distutils.dir_util.copy_tree("dist\\fileop","dist\\falcon")
shutil.rmtree("dist\\fileop")
print("Done!")
