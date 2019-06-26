# -*- coding: utf-8 -*-
#app build tool
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
import os
import sys
import subprocess
import shutil

subprocess.call("pyinstaller --windowed fileop.py")
subprocess.call("rd /s /q build", shell=True)
subprocess.call("move /y dist\\fileop\\* dist\\", shell=True)
subprocess.call("move /y dist\\fileop\\Include dist\\", shell=True)
subprocess.call("move /y dist\\fileop\\win32com dist\\", shell=True)
