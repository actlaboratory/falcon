# -*- coding: utf-8 -*-
#Falcon worker thread tasks
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

"""
ワーカースレッドで実行されるタスクは、ここに並べます。
ワーカースレッドのタスクは、必ず taskState と param という辞書を引数にとり、それを使って処理します。
定期的に taskState.canceled プロパティをチェックして、 True になっていれば、処理を中断しなければなりません。その際には、 False を返します。処理を最後まで実行したら、 True を返す必要があります。
"""

import pathlib
import wx
import globalVars
import misc
import time

def DirCalc(taskState,param):
	"""
		計算結果は(インデックス番号,バイト単位のサイズint値)で返る。
		取得失敗時に-1となる場合があるので要注意
	"""
	lst=param['lst']
	results=[]
	for elem in lst:
		if taskState.canceled: return False
		s=misc.GetDirectorySize(elem[1])
		results.append((elem[0],s))
		#end 成功か失敗か
	#end for
	if taskState.canceled: return False
	wx.CallAfter(param['callback'],results,taskState)
	return True

def GetRecursiveFileList(taskState,param):
	"""
		path から全てのフォルダを再帰的にたどって、ファイル名を out のリストに入れていく。なお、入る値は、 path からの相対パス。
	"""
	out_lst=param['out_lst']
	path=param['path']
	for elem in misc.IteratePaths(path):
		if taskState.canceled: return False
		out_lst.append(str(pathlib.Path(elem).relative_to(path)))
	#end ファイルリストをガンガン入れる
	if taskState.canceled: return False
	globalVars.app.PlaySound("tip.ogg")
	return True

def PerformSearch(taskState,param):
	"""
		検索のバックグラウンド処理。listObject の検索メソッドを実行して、見つかった者を tabObject のほうに通知しながら、リアルタイムな検索結果表示を実現している。
	"""
	l=param['listObject']
	t=param['tabObject']
	while(True):
		if taskState.canceled: return False
		finished,hits=l._performSearchStep()
		if len(hits)>0: wx.CallAfter(t._onSearchHitCallback,hits)
		if finished: break#全て検索した
		time.sleep(0.5)
	#end 検索ループ
	return True

	for elem in misc.IteratePaths(param['path']):
		if taskState.canceled: return False

def DebugBeep(taskState,param):
	for i in range(10):
		if taskState.canceled: return False
		globalVars.app.PlaySound("tip.ogg")
		time.sleep(1)
	#end for
	return True
