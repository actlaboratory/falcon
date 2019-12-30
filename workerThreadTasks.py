# -*- coding: utf-8 -*-
#Falcon worker thread tasks
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
ワーカースレッドで実行されるタスクは、ここに並べます。
ワーカースレッドのタスクは、必ず taskObject と param という辞書を引数にとり、それを使って処理します。
定期的に taskObject.canceled プロパティをチェックして、 True になっていれば、処理を中断しなければなりません。その際には、 False を返します。処理を最後まで実行したら、 True を返す必要があります。
"""

import wx
import globalVars
import time

import misc

def DirCalc(taskObject,param):
	lst=param['lst']
	results=[]
	for elem in lst:
		if taskObject.canceled: return False
		s=misc.GetDirectorySize(elem[1])
		if s==-1:
			results.append((elem[0],_("<取得失敗>")))
		else:
			results.append((elem[0],misc.ConvertBytesTo(s,misc.UNIT_AUTO,True)))
		#end 成功か失敗か
	#end for
	if taskObject.canceled: return False
	wx.CallAfter(param['callback'],results)
	return True

def DebugBeep(taskObject,param):
	for i in range(10):
		if taskObject.canceled: return False
		globalVars.app.PlaySound("tip.ogg")
		time.sleep(1)
	#end for
	return True
