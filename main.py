#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
NET Guard monitors the local network.
Shows a list with all connected devices and warns with an audible alarm when it detects a new or untrusted device.

https://github.com/javidominguez/netGuard

Copyright (C) 2023 Javi Dominguez 
This file is covered by the GNU General Public License.
See the file COPYING for more details.
"""

import gettext
import json
import os
import sys
import winsound
from threading import Event, Thread, Timer
from time import sleep

import wx

from gui import NetScannerFrame
from scanner import LANScanner


class Alarm(Thread):
	def __init__(self):
		super().__init__()
		self.__event = Event()
		self.__flagStop = False

	def run(self):
		while True:
			self.__event.wait()
			if self.__flagStop: break
			f = r"C:\Users\JaviD\Documents\workspace\LAN-scanner\sounds\alarm.wav"
			winsound.PlaySound(f, winsound.SND_FILENAME)
			sleep(0.75)

	def sound(self, timeout=0):
		if not self.__event.isSet():
			self.__event.set()
			if timeout >0:
				Timer(timeout, self.silence).start()

	def silence(self):
		self.__event.clear()

	def kill(self):
		self.__flagStop = True
		self.__event.set()


class Settings(dict):
	def __init__(self, f=""):
		super().__init__()
		self.__settingsFile = f
		if not self.load():
			self["threads"] = 16
			self["timelapse"] = 180
			self["soundEfects"] = True
			self["hotkey"] = { "mainKey": 71, "modifiers": 7}
			self.save()

	def load(self):
		if os.path.exists(self.__settingsFile):
			with open(self.__settingsFile, "r") as f:
				d = json.load(f)
			if d:
				for k in d:
					self[k] = d[k]
			return True
		return False

	def save(self):
		if self.__settingsFile:
			with open(self.__settingsFile, "w") as f:
				json.dump(self, f)
			return True
		return False

	@property
	def file(self):
		return self.__settingsFile


class netScannerApp(wx.App):
	def __init__(self, *args, startWithHiddenWindow=False, **kwargs):

		self.startWithHiddenWindow = startWithHiddenWindow
		self.Name = "NET Guard"
		self.Path = os.path.dirname(os.path.abspath(sys.argv[0]))
		self.IconFile = os.path.join(self.Path, "netGuard.ico")
		super().__init__(*args, **kwargs)

	def OnInit(self):
		settings = Settings(os.path.join(self.Path, "settings.json"))
		scanner = LANScanner(
			threads=settings["threads"],
			timelapse=settings["timelapse"],
			devices=os.path.join(self.Path, "devices.json")
		)
		alarm = Alarm()
		self.frame = NetScannerFrame(None, wx.ID_ANY, self.Name, scanner=scanner, settings=settings, alarm=alarm)
		self.SetTopWindow(self.frame)
		if not self.startWithHiddenWindow:
			self.frame.restore()
		return True

if __name__ == "__main__":
	gettext.install("app")  # replace with the appropriate catalog name

	h = "--hidden" in [i.lower() for i in sys.argv]
	app = netScannerApp(0, startWithHiddenWindow=h)
	app.MainLoop()
