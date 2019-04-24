# -*- coding: utf-8 -*-
#Falcon app GUI implementation
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Note: All comments except these top lines will be written in Japanese. 

import wx
import logging
import sys

class OnExit():

	def __init__(self,hFrame,log):
		self.hFrame=hFrame
		self.hFrame.Bind(wx.EVT_CLOSE,self.onExit)
		self.log=log

	def onExit(self, event=None):
		"""アプリケーションを終了させる。"""
		self.log.info("Exiting Frame...")
		self.log.info("Bye bye!")
		sys.exit()



