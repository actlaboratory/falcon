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
		s=misc.GetDirectorySize(elem[1])
		if s==-1:
			results.append((elem[0],_("<取得失敗>")))
		else:
			results.append((elem[0],misc.ConvertBytesTo(s,misc.UNIT_AUTO,True)))
		#end 成功か失敗か
	#end for
	wx.CallAfter(param['callback'],results)
