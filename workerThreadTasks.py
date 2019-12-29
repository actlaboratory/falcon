# -*- coding: utf-8 -*-
#Falcon worker thread tasks
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
ワーカースレッドで実行されるタスクは、ここに並べます。ワーカースレッドのタスクは、必ず param という辞書を引数にとり、それを使って処理します。
"""

import wx

import misc

def DirCalc(param):
	lst=param['lst']
	results=[]
	for elem in lst:
		results.append((elem[0],misc.GetDirectorySize(elem[1])))
	#end for
	wx.CallAfter(param['callback'],results)
