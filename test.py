# -*- coding: utf-8 -*-
#Falcon startup file
#run python fal.py to execute Falcon
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#See window.py for application entry point
import listObjects

l=listObjects.DriveList()
l.Initialize()
print(l.GetItems())
