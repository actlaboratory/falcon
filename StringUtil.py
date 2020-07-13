# -*- coding: utf-8 -*-
#Falcon String Utility
#Copyright (C) 2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

#UTF-8のバイト列bのインデックスiの位置から始まる文字の(バイト数,幅)を返す
#幅はASCIIと半角カタカナだけ1、他は2を返す
def _GetWidth(b,i):
	c=b[i]

	#cを基に、その文字のバイト数を求める
	if c<0x80:clen=1
	elif c<0xE0:clen=2
	elif c<0xF0:clen=3
	else: clen=4

	#その文字の幅を求める
	if clen==1:
		width=1
	elif clen==3:
		if b[i] == 0xEF and b[i+1] >= 0xBC and b[i+2] >= 0x80:
			width=1
		else:
			width=2
	else:
		width=2
	return clen,width

def GetLimitedString(s,l):
	"""
		文字列sの先頭から、半角l文字分の幅まで取得
		収まらない場合、末尾に「...」が入り、この「...」の長さもlに含む
	"""
	l=int(l)

	bytes=bytearray(s.encode())
	resultCount=0				#カーソル直前までの文字幅合計(半角でカウント)
	cursor=0					#カーソル位置

	while(resultCount<=l-3 and cursor<len(bytes)):
		clen,width=_GetWidth(bytes,cursor)
		if resultCount+width<=l-3:	#カーソルを進め、resultCountを加算
			cursor+=clen
			resultCount+=width
		else:						#文字数オーバーする
			break

	#残りの文字が半角3文字以内ならそのままでよい
	exCount=0
	exCursor=cursor
	while(exCount+resultCount<l and exCursor<len(bytes)):
		clen,width=_GetWidth(bytes,exCursor)
		if exCount+width+resultCount<=l:	#カーソルを進め、resultCountを加算
			exCursor+=clen
			exCount+=width
		else:						#文字数オーバーする
			break
	if exCursor>=len(bytes):
		return s					#入力のまま

	#"..."を入れる
	for i in range(3):
		if cursor<len(bytes):
			bytes[cursor]=46	#.のASCIIコード46
		else:
			bytes.append(46)
		cursor+=1

	#cursor以下の文字をカットして返す
	while(cursor<len(bytes)):
		bytes[cursor]=0
		cursor+=1
	return bytes.decode()

def GetWidthCount(s):
	"""
		文字列sの幅を半角=1・全角=2で計算して返す。
		計算方法は_GetWidth()に準じる
	"""
	result=0
	cursor=0
	bytes=bytearray(s.encode())
	while(cursor<len(bytes)):
		clen,width=_GetWidth(bytes,cursor)
		cursor+=clen
		result+=width
	return result
