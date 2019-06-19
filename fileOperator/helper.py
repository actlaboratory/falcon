# -*- coding: utf-8 -*-
#Falcon file operation handler helper
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

from . import failedElement

#ヘルパー関数
def IsAccessDenied(err):
	"""このエラーオブジェクトが、アクセス拒否(権限昇格が必要)なエラーならTrueを帰す。"""
	import winerror
	s=str(err)
	s=s.lstrip("(")
	return int(s.split(",")[0])==winerror.ERROR_ACCESS_DENIED

def CommonFailure(output,elem,err,log):
	"""共通の失敗処理。"""
	log.error("file op error %s %s" % (elem, str(err)))
	if IsAccessDenied(err):#アクセス拒否ならリトライへ
		output["retry"].append(failedElement.FailedElement(elem,str(err)))
	else:#失敗へ
		output["failed"].append(failedElement.FailedElement(elem,str(err)))
		output["all_OK"]=False
