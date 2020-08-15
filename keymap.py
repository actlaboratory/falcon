# -*- coding: utf-8 -*-
#Falcon key map management
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>
#Note: All comments except these top lines will be written in Japanese. 

import configparser
import logging
import os
import wx
import defaultKeymap
import errorCodes
import menuItemsStore

import tabs
import browsableObjects

from simpleDialog import *

str2ControlCommand={
	#制御キー
	"CONTROL_A":wx.WXK_CONTROL_A,
	"CONTROL_B":wx.WXK_CONTROL_B,
	"CONTROL_C":wx.WXK_CONTROL_C,
	"CONTROL_D":wx.WXK_CONTROL_D,
	"CONTROL_E":wx.WXK_CONTROL_E,
	"CONTROL_F":wx.WXK_CONTROL_F,
	"CONTROL_G":wx.WXK_CONTROL_G,
	"CONTROL_H":wx.WXK_CONTROL_H,
	"CONTROL_I":wx.WXK_CONTROL_I,
	"CONTROL_J":wx.WXK_CONTROL_J,
	"CONTROL_K":wx.WXK_CONTROL_K,
	"CONTROL_L":wx.WXK_CONTROL_L,
	"CONTROL_M":wx.WXK_CONTROL_M,
	"CONTROL_N":wx.WXK_CONTROL_N,
	"CONTROL_O":wx.WXK_CONTROL_O,
	"CONTROL_P":wx.WXK_CONTROL_P,
	"CONTROL_Q":wx.WXK_CONTROL_Q,
	"CONTROL_R":wx.WXK_CONTROL_R,
	"CONTROL_S":wx.WXK_CONTROL_S,
	"CONTROL_T":wx.WXK_CONTROL_T,
	"CONTROL_U":wx.WXK_CONTROL_U,
	"CONTROL_V":wx.WXK_CONTROL_V,
	"CONTROL_W":wx.WXK_CONTROL_W,
	"CONTROL_X":wx.WXK_CONTROL_X,
	"CONTROL_Y":wx.WXK_CONTROL_Y,
	"CONTROL_Z":wx.WXK_CONTROL_Z
}

#マウスボタン
str2MouseKey={
	"LBUTTON":wx.WXK_LBUTTON,
	"MBUTTON":wx.WXK_MBUTTON,
	"RBUTTON":wx.WXK_RBUTTON
}

#他の全てのキーの修飾キーとして利用可能
str2ModifierKey={
	#修飾キー
	"ALT":wx.WXK_ALT,
	"CONTROL":wx.WXK_CONTROL,
	"WINDOWS_LEFT":wx.WXK_WINDOWS_LEFT,
	"WINDOWS_RIGHT":wx.WXK_WINDOWS_RIGHT,
	"SHIFT":wx.WXK_SHIFT
}

#不明なもの・Windowsでは使えないもの、
str2UnknownKey={
	"START":wx.WXK_START,					#Ctrl+ESC
	"CANCEL":wx.WXK_CANCEL,
	"MENU":wx.WXK_MENU,
	"PAUSE":wx.WXK_PAUSE,
	"CAPITAL":wx.WXK_CAPITAL,
	"SELECT":wx.WXK_SELECT,
	"PRINT":wx.WXK_PRINT,
	"EXECUTE":wx.WXK_EXECUTE,
	"HELP":wx.WXK_HELP,
	"SCROLL":wx.WXK_SCROLL,					#ScrLk
	"COMMAND":wx.WXK_COMMAND,				#CONTROLと同じ
	"RAW_CONTROL":wx.WXK_RAW_CONTROL,		#CONTROLと同じ
	"NUMPAD_BEGIN":wx.WXK_NUMPAD_BEGIN,
	"CLEAR":wx.WXK_CLEAR,					#テンキー5

	#記号キー 動作しない
	"MULTIPLY":wx.WXK_MULTIPLY,
	"ADD":wx.WXK_ADD,
	"SEPARATOR":wx.WXK_SEPARATOR,
	"SUBTRACT":wx.WXK_SUBTRACT,
	"DECIMAL":wx.WXK_DECIMAL,
	"DIVIDE":wx.WXK_DIVIDE,
}

#単独でも修飾キーとの組み合わせでも利用可能
str2FunctionKey={
	#ファンクションキー
	"F1":wx.WXK_F1,
	"F2":wx.WXK_F2,
	"F3":wx.WXK_F3,
	"F4":wx.WXK_F4,
	"F5":wx.WXK_F5,
	"F6":wx.WXK_F6,
	"F7":wx.WXK_F7,
	"F8":wx.WXK_F8,
	"F9":wx.WXK_F9,
	"F10":wx.WXK_F10,
	"F11":wx.WXK_F11,
	"F12":wx.WXK_F12,
	"F13":wx.WXK_F13,
	"F14":wx.WXK_F14,
	"F15":wx.WXK_F15,
	"F16":wx.WXK_F16,
	"F17":wx.WXK_F17,
	"F18":wx.WXK_F18,
	"F19":wx.WXK_F19,
	"F20":wx.WXK_F20,
	"F21":wx.WXK_F21,
	"F22":wx.WXK_F22,
	"F23":wx.WXK_F23,
	"F24":wx.WXK_F24,

	#テンキーファンクションキー
	"NUMPAD_F1":wx.WXK_NUMPAD_F1,
	"NUMPAD_F2":wx.WXK_NUMPAD_F2,
	"NUMPAD_F3":wx.WXK_NUMPAD_F3,
	"NUMPAD_F4":wx.WXK_NUMPAD_F4,
}

#文字入力時に利用できない単独キー
str2InputControlKey={
	"BACK":wx.WXK_BACK,
	"SPACE":wx.WXK_SPACE,
	"DELETE":wx.WXK_DELETE,
	"INSERT":wx.WXK_INSERT,			#NUMPAD_INSERTと同時に反応するので注意

	#テンキー
	"NUMPAD_SPACE":wx.WXK_NUMPAD_SPACE,
	"NUMPAD_INSERT":wx.WXK_NUMPAD_INSERT,
	"NUMPAD_DELETE":wx.WXK_NUMPAD_DELETE,

	#矢印キー
	"LEFTARROW":wx.WXK_LEFT,
	"UPARROW":wx.WXK_UP,
	"RIGHTARROW":wx.WXK_RIGHT,
	"DOWNARROW":wx.WXK_DOWN,
	"NUMPAD_LEFT":wx.WXK_NUMPAD_LEFT,	#4
	"NUMPAD_UP":wx.WXK_NUMPAD_UP,		#8
	"NUMPAD_RIGHT":wx.WXK_NUMPAD_RIGHT,	#6
	"NUMPAD_DOWN":wx.WXK_NUMPAD_DOWN,	#2

	#ジャンプキー
	"HOME":wx.WXK_HOME,
	"END":wx.WXK_END,
	"PAGEUP":wx.WXK_PAGEUP,
	"PAGEDOWN":wx.WXK_PAGEDOWN,
	"NUMPAD_PAGEUP":wx.WXK_NUMPAD_PAGEUP,#9
	"NUMPAD_PAGEDOWN":wx.WXK_NUMPAD_PAGEDOWN,#3
	"NUMPAD_HOME":wx.WXK_NUMPAD_HOME,	#7
	"NUMPAD_END":wx.WXK_NUMPAD_END,		#9
}

#主要キー
str2StandaloneKey={
	"TAB":wx.WXK_TAB,
	"RETURN":wx.WXK_RETURN,
	"ESCAPE":wx.WXK_ESCAPE,
	"APPLICATIONS":wx.WXK_WINDOWS_MENU,		#コンテキストメニューを開くアプリケーションキー
	"SNAPSHOT":wx.WXK_SNAPSHOT,		#PrintScr

	#テンキー
	"NUMPAD_TAB":wx.WXK_NUMPAD_TAB,
	"NUMPAD_ENTER":wx.WXK_NUMPAD_ENTER,
}

#単独または修飾キーとの組み合わせで利用できる
str2SpecialKey={
	#メディア制御キー
	"VOLUME_DOWN":wx.WXK_VOLUME_DOWN,
	"VOLUME_MUTE":wx.WXK_VOLUME_MUTE,
	"VOLUME_UP":wx.WXK_VOLUME_UP,
	"MEDIA_NEXT":wx.WXK_MEDIA_NEXT_TRACK,
	"MEDIA_PLAY":wx.WXK_MEDIA_PLAY_PAUSE,
	"MEDIA_BACK":wx.WXK_MEDIA_PREV_TRACK,
	"MEDIA_STOP":wx.WXK_MEDIA_STOP,

	#ブラウザ制御キー
	"BROWSER_BACK":wx.WXK_BROWSER_BACK,
	"BROWSER_FAVORITES":wx.WXK_BROWSER_FAVORITES,
	"BROWSER_FORWARD":wx.WXK_BROWSER_FORWARD,
	"BROWSER_HOME":wx.WXK_BROWSER_HOME,
	"BROWSER_REFRESH":wx.WXK_BROWSER_REFRESH,
	"BROWSER_SEARCH":wx.WXK_BROWSER_SEARCH,
	"BROWSER_STOP":wx.WXK_BROWSER_STOP,

	#アプリケーション起動キー
	"LAUNCH_APP1":wx.WXK_LAUNCH_APP1,
	"LAUNCH_APP2":wx.WXK_LAUNCH_APP2,
	"LAUNCH_MAIL":wx.WXK_LAUNCH_MAIL,

	#スペシャル
	"SPECIAL1":wx.WXK_SPECIAL1,
	"SPECIAL2":wx.WXK_SPECIAL2,
	"SPECIAL3":wx.WXK_SPECIAL3,
	"SPECIAL4":wx.WXK_SPECIAL4,
	"SPECIAL5":wx.WXK_SPECIAL5,
	"SPECIAL6":wx.WXK_SPECIAL6,
	"SPECIAL7":wx.WXK_SPECIAL7,
	"SPECIAL8":wx.WXK_SPECIAL8,
	"SPECIAL9":wx.WXK_SPECIAL9,
	"SPECIAL10":wx.WXK_SPECIAL10,
	"SPECIAL11":wx.WXK_SPECIAL11,
	"SPECIAL12":wx.WXK_SPECIAL12,
	"SPECIAL13":wx.WXK_SPECIAL13,
	"SPECIAL14":wx.WXK_SPECIAL14,
	"SPECIAL15":wx.WXK_SPECIAL15,
	"SPECIAL16":wx.WXK_SPECIAL16,
	"SPECIAL17":wx.WXK_SPECIAL17,
	"SPECIAL18":wx.WXK_SPECIAL18,
	"SPECIAL19":wx.WXK_SPECIAL19,
	"SPECIAL20":wx.WXK_SPECIAL20,
}

#他の修飾キーとの組み合わせで利用できるキー
str2CharactorKey={
	#アルファベットキー
	"A": ord('A'),
	"B": ord('B'),
	"C": ord('C'),
	"D": ord('D'),
	"E": ord('E'),
	"F": ord('F'),
	"G": ord('G'),
	"H": ord('H'),
	"I": ord('I'),
	"J": ord('J'),
	"K": ord('K'),
	"L": ord('L'),
	"M": ord('M'),
	"N": ord('N'),
	"O": ord('O'),
	"P": ord('P'),
	"Q": ord('Q'),
	"R": ord('R'),
	"S": ord('S'),
	"T": ord('T'),
	"U": ord('U'),
	"V": ord('V'),
	"W": ord('W'),
	"X": ord('X'),
	"Y": ord('Y'),
	"Z": ord('Z'),

	#数字キー
	"0": ord('0'),
	"1": ord('1'),
	"2": ord('2'),
	"3": ord('3'),
	"4": ord('4'),
	"5": ord('5'),
	"6": ord('6'),
	"7": ord('7'),
	"8": ord('8'),
	"9": ord('9'),

	#テンキー数字キー
	"NUMPAD0":wx.WXK_NUMPAD0,
	"NUMPAD1":wx.WXK_NUMPAD1,
	"NUMPAD2":wx.WXK_NUMPAD2,
	"NUMPAD3":wx.WXK_NUMPAD3,
	"NUMPAD4":wx.WXK_NUMPAD4,
	"NUMPAD5":wx.WXK_NUMPAD5,
	"NUMPAD6":wx.WXK_NUMPAD6,
	"NUMPAD7":wx.WXK_NUMPAD7,
	"NUMPAD8":wx.WXK_NUMPAD8,
	"NUMPAD9":wx.WXK_NUMPAD9,

	#記号キー
	",": ord(','),
	".": ord('.'),
	"/": ord('/'),
	"\\": ord('\\'),	#上段側のみにマッチ
	";": ord(';'),
	":": ord(':'),
	"[": ord('['),
	"]": ord(']'),
	"@": ord('@'),
	"-": ord('-'),
	"^": ord('^'),

	#テンキー記号キー
	"NUMPAD_EQUAL":wx.WXK_NUMPAD_EQUAL,
	"NUMPAD_MULTIPLY":wx.WXK_NUMPAD_MULTIPLY,
	"NUMPAD_ADD":wx.WXK_NUMPAD_ADD,
	"NUMPAD_SEPARATOR":wx.WXK_NUMPAD_SEPARATOR,
	"NUMPAD_SUBTRACT":wx.WXK_NUMPAD_SUBTRACT,
	"NUMPAD_DECIMAL":wx.WXK_NUMPAD_DECIMAL,
	"NUMPAD_DIVIDE":wx.WXK_NUMPAD_DIVIDE,
}

#利用不可
str2categoryKey={
	#カテゴリ制御キー
	"CATEGORY_ARROW":wx.WXK_CATEGORY_ARROW,
	"CATEGORY_CUT":wx.WXK_CATEGORY_CUT,
	"CATEGORY_JUMP":wx.WXK_CATEGORY_JUMP,
	"CATEGORY_NAVIGATION":wx.WXK_CATEGORY_NAVIGATION,
	"CATEGORY_PAGING":wx.WXK_CATEGORY_PAGING,
	"CATEGORY_TAB":wx.WXK_CATEGORY_TAB,
}

str2key={}
str2key.update(**str2ControlCommand,**str2MouseKey,**str2ModifierKey,**str2UnknownKey,**str2FunctionKey,**str2InputControlKey,**str2StandaloneKey,**str2SpecialKey,**str2CharactorKey,**str2categoryKey)

class KeymapHandler():
	"""wxのアクセラレーターテーブルを生成します。"""

	def __init__(self,dict=None):
		#wx.AcceleratorEntry.__eq__=AcceleratorEntry_eq
		self.log=logging.getLogger("falcon.keymapHandler")
		self.errors={}
		self.entries={}		#生成したAcceleratorEntry
		self.map={}			#ref番号→ショートカットキーに変換
		self.refMap={}		#キーの重複によりこのインスタンスで処理する必要のあるメニューと、そのとび先の本来のref

		if dict:
			read=configparser.ConfigParser()
			read.read_dict(defaultKeymap.defaultKeymap)
			for identifier in read.sections():
				for elem in read.items(identifier):
					self.add(identifier,elem[0],elem[1])

	def addFile(self, filename):
		"""
			指定されたファイルを読もうと試みます。ファイルが見つからなかった場合は、FILE_NOT_FOUND を返します。ファイルがパースできなかった場合は、PARSING_FAILED を返します。
			errorCodes.OKが返された場合であっても、キーの重複などで追加できなかったものがあった可能性があります。これについては、その情報がself.errorsに格納されるので呼出元で検証する必要があります。
		"""
		if not os.path.exists(filename):
			self.log.warning("Cannot find %s" % filename)
			return errorCodes.FILE_NOT_FOUND
		newKeys=configparser.ConfigParser()
		ret=newKeys.read(filename, encoding="UTF-8")
		ret= errorCodes.OK if len(ret)>0 else errorCodes.PARSING_FAILED
		if ret==errorCodes.PARSING_FAILED:
			self.log.warning("Cannot parse %s" % filename)
			return ret

		#newKeysの情報を、検証しながらaddしていく
		for identifier in newKeys.sections():
			for elem in newKeys.items(identifier):
				self.add(identifier,elem[0],elem[1])
		return errorCodes.OK

	def GetError(self,identifier):
		"""指定されたビューのエラー内容を返し、内容をクリアする"""
		identifier=identifier.upper()
		try:
			ret=self.errors[identifier]
		except KeyError:
			return {}
		self.errors[identifier]={}
		return ret

	def add(self,identifier,ref,key):
		"""重複をチェックしながらキーマップにショートカットを追加します。"""

		#refとidentifierは大文字・小文字の区別をしないので大文字に統一
		ref=ref.upper()
		identifier=identifier.upper()

		#identifierが新規だった場合、self.mapとself.entriesにセクション作成
		if not identifier in self.map.keys():
			self.entries[identifier]=[]
			self.map[identifier]={}

		#エントリーの作成・追加
		for e in key.split("/"):
			entry=self.makeEntry(ref,e)
			if entry==False:
				self.addError(identifier,ref,key)
				continue

			#キーの重複確認
			checkList=[]		#要確認リスト
			for i in self.entries[identifier]:
				if entry==i:
					checkList.append(i)
			if checkList:
					checkList.append(entry)
					if self.checkConfrict(checkList,identifier):
						entry=None
					else:
						self.addError(identifier,ref,key)
						continue

			#GetKeyStringに備えてself.mapに追加
			if ref in self.map[identifier]:
				#refが重複の場合、既存のself.map上のエントリの末尾に追加
				self.map[identifier][ref]=self.map[identifier][ref]+"/"+e
			else:
				#self.mapに新規エントリとして追加
				self.map[identifier][ref]=e

			#self.entriesに追加
			#重複確認・置換処理の関係でNoneになってる場合には既に追加済みを意味するのでここでは何もしない
			if entry:
				self.entries[identifier].append(entry)
		return

	def addError(self,identifier,ref,key):
		"""エラー発生時、情報を記録します。"""
		try:
			self.errors[identifier][ref]=key
		except KeyError:
			self.errors[identifier]={}
			self.errors[identifier][ref]=key

	def GetKeyString(self,identifier,ref):
		"""指定されたコマンドのショートカットキー文字列を取得します。"""
		ref=ref.upper()
		identifier=identifier.upper()

		try:
			r=self.map[identifier][ref]
		except KeyError:
			r=None
		#end except
		return r

	def makeEntry(self,ref,key):
		"""ref(String)と、/区切りでない単一のkey(String)からwx.AcceleratorEntryを生成"""
		key=key.upper()
		ctrl="CTRL+" in key
		alt="ALT+" in key
		shift="SHIFT+" in key
		codestr=key.split("+")
		flags=0
		flagCount=0
		if ctrl:
			flags=wx.ACCEL_CTRL
			flagCount+=1
		if alt:
			flags=flags|wx.ACCEL_ALT
			flagCount+=1
		if shift:
			flags=flags|wx.ACCEL_SHIFT
			flagCount+=1
		if not len(codestr)-flagCount==1:
			return False
		codestr=codestr[len(codestr)-1]
		if not codestr in str2key:
			return False
		return AcceleratorEntry(flags,str2key[codestr],menuItemsStore.getRef(ref.upper()),ref.upper())

	def GetTable(self, identifier):
		"""アクセラレーターテーブルを取得します。identifier で、どのビューでのテーブルを取得するかを指定します。"""
		identifier=identifier.upper()
		return wx.AcceleratorTable(self.entries[identifier])

	#複数メニューに対するキーの割り当ての重複を許すか否かを調べる
	#itemsには調べたいAcceleratorEntryのリストを入れる
	def checkConfrict(self,items,identifier):
		flg=0
		for i in [j.refName for j in items]:
			iFlag=0
			if i not in tabs.base.FalconTabBase.selectItemTypeMenuConditions[browsableObjects.File]:
				iFlag+=1
			if i not in tabs.base.FalconTabBase.selectItemTypeMenuConditions[browsableObjects.Folder]:
				iFlag+=2
			if i not in tabs.streamList.StreamListTab.blockMenuList:
				iFlag+=4
			if i not in tabs.driveList.DriveListTab.blockMenuList:
				iFlag+=8
			#print(i+":"+str(iFlag))
			if iFlag&flg==0:
				flg+=iFlag
			else:
				#重複によるエラー
				self.log.debug("key confricted. "+i+" is confrict in "+str(items))
				return False
		self.log.debug("key not confricted. "+i+" is not confrict in "+str(items))

		#重複してるが問題なしの場合
		#refを書き換える
		newref=menuItemsStore.getRef("keymap_"+items[0].ToRawString())
		self.refMap[newref]=[]

		#self.entriesからいったん削除
		for i in range(len(items)-1):
			self.entries[identifier].remove(items[0])

		#refを差し替えて再登録
		for i in items:
			self.refMap[newref].append(i.GetCommand())
			self.entries[identifier].append(AcceleratorEntry(i.GetFlags(),i.GetKeyCode(),newref,i.GetRefName()))
		return True

	def isRefHit(self,ref):
		return ref in self.refMap

	def GetOriginalRefs(self,ref):
		return self.refMap[ref]

class AcceleratorEntry(wx.AcceleratorEntry):
	#ショートカットキーの一致によって判定され、登録されたメニューコマンドの一致は無視される
	#refをstrで保持する

	def __init__(self,flags,key,cmd,refName=""):
		super().__init__(flags,key,cmd)
		self.refName=refName

	def __eq__(self,other):
		# isinstance(other, Person)を除去
		if other is None or type(self) != type(other): return False
		if self.GetFlags()==other.GetFlags() and self.GetKeyCode()==other.GetKeyCode():
			return True
		return False

	def GetRefName(self):
		return self.refName


class KeyFilter:
	"""
		利用できるショートカットキーを制限するためのフィルタ
	"""

	def __init__(self):
		"""
			必用な変数を作成し、OSが利用するコマンドとの重複は設定できないようブロックします。
		"""
		self.modifierKey=set()								#有効な修飾キー
		self.functionKey=set()								#有効なファンクションキー。単独または修飾キーとの組み合わせで利用可能
		self.enableKey=set()								#修飾キーとの組み合わせで利用可能
		self.noShiftEnableKey=set()							#SHIFTキー以外の修飾キーとの組み合わせで利用可能(modifierKeyにSHIFTを指定していない場合は無視される)
		self.disablePattern=set()							#無効なキーの組み合わせ
		self.disablePattern.add("CONTROL+ESCAPE")			#スタートメニュー
		self.disablePattern.add("CONTROL+SHIFT+ESCAPE")		#タスクマネージャ
		self.disablePattern.add("CONTROL+WINDOWS+ENTER")	#ナレーターの起動と終了
		self.disablePattern.add("ALT+SHIFT+SNAPSHOT")		#ハイコントラストの切り替え
		self.disablePattern.add("ALT+ESCAPE")				#最前面ウィンドウの最小化

	def SetUserMode(self):
		"""
			ユーザが独自にキーをカスタマイズする場合に、指定することが望ましくないキーの組み合わせをブロックします。
			将来、開発者が機能拡張する際の問題を和らげることを目的としています。
			なお、開発者であってもコメントで記した目的以外に利用することは避けるべきです。
		"""
		self.disablePattern.add("APPLICATIONS")				#コンテキストメニューの表示
		self.disablePattern.add("SHIFT+F10")				#コンテキストメニューの表示
		self.disablePattern.add("F10")						#ALTキーの代わり
		self.disablePattern.add("ESCAPE")					#操作の取り消し
		self.disablePattern.add("ALT+F4")					#アプリケーションの終了
		self.disablePattern.add("ALT+SPACE")				#リストビュー等で全ての選択を解除
		return self

	def SetDefault(self,supportInputChar):
		"""
			フィルタを一般的な設定に構成します。
			supportInputCharには、そのウィンドウでの文字入力の可否を設定します。
		"""
		self.modifierKey.add("CONTROL")
		self.modifierKey.add("ALT")
		self.modifierKey.add("SHIFT")

		self.functionKey|=str2FunctionKey.keys()
		self.functionKey|=str2SpecialKey.keys()
		self.noShiftEnableKey|=str2CharactorKey.keys()
		self.enableKey|=str2StandaloneKey.keys()

		if supportInputChar:
			#文字入力に関わる共通のショートカットは設定不可
			self.disablePattern.add("CONTROL+INSERT")		#コピー
			self.disablePattern.add("SHIFT+INSERT")			#貼り付け
			self.disablePattern.add("CONTROL+Z")			#元に戻す
			self.disablePattern.add("CONTROL+X")			#切り取り
			self.disablePattern.add("CONTROL+C")			#コピー
			self.disablePattern.add("CONTROL+V")			#貼り付け
			self.disablePattern.add("CONTROL+A")			#すべて選択
			self.disablePattern.add("CONTROL+Y")			#やり直し
			self.disablePattern.add("CONTROL+F7")			#単語登録(日本語変換時のみ)
			self.disablePattern.add("CONTROL+F10")			#IMEメニュー表示(日本語変換時のみ)

			#単独で文字入力の制御に利用されるので修飾キー必須
			self.enableKey|=str2InputControlKey.keys()
		else:
			#単独で文字入力の制御に利用されるが、それがないなら単独利用可能
			self.functionKey|=str2InputControlKey.keys()

		return self


