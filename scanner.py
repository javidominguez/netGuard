#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Net scanner module for NET Guard application.

NET Guard monitors the local network.
Shows a list with all connected devices and warns with an audible alarm when it detects a new or untrusted device.

https://github.com/javidominguez/netGuard

Copyright (C) 2023 Javi Dominguez 
This file is covered by the GNU General Public License.
See the file COPYING for more details.
"""

import json
import os
from socket import gethostbyname, gethostname
from threading import Lock, Thread, enumerate
from time import sleep, time

import wx.lib.newevent
from getmac import get_mac_address


Event_DeviceFound, EVT_DEVICE_FOUND = wx.lib.newevent.NewEvent()
Event_UnknownDeviceAlert, EVT_UNKNOWN_DEVICE_ALERT = wx.lib.newevent.NewEvent()
Event_UntrustedDeviceAlert, EVT_UNTRUSTED_DEVICE_ALERT = wx.lib.newevent.NewEvent()
Event_ScanCycleStart, EVT_SCAN_CYCLE_START = wx.lib.newevent.NewEvent()
Event_ScanCycleFinish, EVT_SCAN_CYCLE_FINISH = wx.lib.newevent.NewEvent()

DEVICE_INFO_NAME = 0
DEVICE_INFO_TRUST_LEVEL = 1
DEVICE_INFO_FIRST_DETECTED = 2
DEVICE_INFO_LAST_DETECTED = 3

TRUST_LEVEL_RED = 0
TRUST_LEVEL_YELLOW = 1
TRUST_LEVEL_GREEN = 2

class LANScanner(Thread):
	def __init__(self, timelapse=180, threads=8, devices=""):
		Thread.__init__(self)
		self.name = "LAN Scanner"
		self.setDaemon(True)
		self.flagStop = False
		self.flagWait = False
		self.lock = Lock()
		self.__timelapse = timelapse
		self.__nThreads = threads
		self.__arp = []
		self.__devicesFile = devices
		if os.path.exists(devices):
			with open(devices, "r") as f:
				self.__devices = json.load(f)
		else:
			self.__devices = {}
		self.__EventHandler = None
		self.__eventDeviceFound = Event_DeviceFound()
		self.__eventUnknownDeviceAlert = Event_UnknownDeviceAlert()
		self.__eventUntrustedDeviceAlert = Event_UntrustedDeviceAlert()
		self.__event_ScanCycleStart = Event_ScanCycleStart()
		self.__event_ScanCycleFinish = Event_ScanCycleFinish()

	def run(self):
		ip = gethostbyname(gethostname())
		ip = ip.split(".")[:-1]
		while True:
			if self.flagStop: break
			if self.__EventHandler:
				wx.PostEvent(self.__EventHandler, self.__event_ScanCycleStart)
			self.__arp.clear()
			scanChunkThreads=[]
			for r in range (1, 257, 256//self.__nThreads):
				scanChunkThreads.append(GetMACThread(
					parent=self,
					lock=self.lock,
					ipRange=[".".join(ip+[str(i)]) for i in range (r,r+256//self.__nThreads)]
				))
			for th in scanChunkThreads:
				th.start()
			for th in scanChunkThreads:
				th.join()
			if self.__EventHandler:
				wx.PostEvent(self.__EventHandler, self.__event_ScanCycleFinish)
			self.saveDevices()
			self.flagWait = True
			for remaindTime in range(self.__timelapse, 0, -1):
				if not self.flagWait or self.flagStop: break
				sleep(1.0)
			self.flagWait = False

	def bind(self, handler):
		self.__EventHandler = handler

	def update(self, ip, mac):
		if ip.split(".")[-1] == "255": return
		self.__arp.append((ip, mac))
		self.updateDevices(mac, last=time())
		if self.__EventHandler:
			wx.PostEvent(self.__EventHandler, self.__eventDeviceFound)
			if self.__devices[mac][DEVICE_INFO_TRUST_LEVEL] == TRUST_LEVEL_RED:
				wx.PostEvent(self.__EventHandler, self.__eventUntrustedDeviceAlert)

	def updateDevices(self, mac, name="", trustLevel=-1, first=None, last=None, save=False):
		if mac in self.__devices:
			device_name, device_reliability, device_first, device_last = self.__devices[mac]
			device_name = name if name else device_name
			device_reliability = trustLevel if trustLevel >= 0 else device_reliability
			device_first = first if first else device_first
			device_last = last if last else device_last
			self.__devices[mac] = (device_name, device_reliability, device_first, device_last)
		else:
			if not last: last = time()
			if not first: first = last
			if trustLevel < 0: trustLevel = TRUST_LEVEL_RED
			self.__devices[mac] = (name, trustLevel, first, last)
			if self.__EventHandler:
				wx.PostEvent(self.__EventHandler, self.__eventUnknownDeviceAlert)
		if save: self.saveDevices()

	def saveDevices(self):
		if self.__devicesFile:
			with open(self.__devicesFile, "w") as f:
				json.dump(self.__devices, f)
			return True
		return False

	def kill(self):
		self.flagStop = True

	@property
	def arp(self):
		with self.lock:
			arp = self.__arp.copy()
		def k(item):
			return int(item[0].split(".")[-1])
		arp.sort(key=k)
		return arp

	@property
	def devices(self):
		with self.lock:
			d = self.__devices
		return d

	@property
	def timelapse(self):
		return self.__timelapse

	@timelapse.setter
	def timelapse(self, value):
		if not isinstance(value, int): raise TypeError("An int was expected")
		if value<60 or value>900: raise ValueError("The supported range is 60-900")
		self.__timelapse = value

	@property
	def threads(self):
		return self.__nThreads

	@threads.setter
	def threads(self, value):
		if not isinstance(value, int): raise TypeError("An int was expected")
		if not value in (4, 8, 16, 32 , 64): raise ValueError("Unsupported value")
		self.__nThreads = value

class GetMACThread(Thread):
	def __init__(self, parent, lock, ipRange):
		Thread.__init__(self)
		self.name = "Scanning range {}-{}".format(
			ipRange[0], ipRange[-1].split(".")[-1]
		)
		self.setDaemon(True)
		self.ipRange = ipRange
		self.parent = parent
		self.lock = lock

	def run(self):
		for ip_address in self.ipRange:
			if self.parent.flagStop: break
			mac = get_mac_address(ip=ip_address)
			if mac:
				with self.lock:
					self.parent.update(ip_address, mac)

