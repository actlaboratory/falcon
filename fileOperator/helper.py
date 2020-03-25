# -*- coding: utf-8 -*-
#Falcon file operation handler helper
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

from . import failedElement
import winerror

#ヘルパー関数
def GetErrorNumber(err):
	"""windows 例外文字列から、エラーナンバーを取得する。"""
	if isinstance(err,int): return err
	s=str(err)
	s=s.lstrip("(")
	return int(s.split(",")[0])

def IsAccessDenied(num):
	"""エラーナンバーから、アクセス拒否のエラーかどうかを調べる。"""
	return num in (winerror.ERROR_ACCESS_DENIED, winerror.ERROR_PRIVILEGE_NOT_HELD) 

def AppendFailed(op,elem,num):
	"""失敗したリストに項目を追加。"""
	op.output["failed"].append(failedElement.FailedElement(elem,(num,"fail")))
	op.output["all_OK"]=False

def CommonFailure(op,elem,err,log):
	"""共通の失敗処理。"""
	log.error("file op error %s %s" % (elem, str(err)))
	r=IsAccessDenied(GetErrorNumber(err))
	if not r:
		AppendFailed(op,elem,0)
	else:
		if op.elevated: AppendFailed(op,elem,0)#昇格してる状態でも無理だった
	#end denied かどうか
	return r

