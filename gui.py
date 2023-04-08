#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
GUI for NET Guard application.

NET Guard monitors the local network.
Shows a list with all connected devices and warns with an audible alarm when it detects a new or untrusted device.

https://github.com/javidominguez/netGuard

Copyright (C) 2023 Javi Dominguez 
This file is covered by the GNU General Public License.
See the file COPYING for more details.
"""

import gettext
import locale
import os
import sys
import winsound
from datetime import datetime, timedelta
from threading import Thread

import pyperclip
import wx
import wx.adv

from scanner import *


class SettingsDialog(wx.Dialog):
	def __init__(self, *args, threads=2, timelapse=2, soundEfects=True, **kwargs):
		kwargs["style"] = kwargs.get("style", 0) | wx.DEFAULT_DIALOG_STYLE
		wx.Dialog.__init__(self, *args, **kwargs)
		self.SetTitle(_("Settings"))

		mainSizer = wx.BoxSizer(wx.VERTICAL)

		gridSizer = wx.GridSizer(2, 2, 0, 0)
		mainSizer.Add(gridSizer, 1, wx.EXPAND, 0)

		label_threads = wx.StaticText(self, wx.ID_ANY, _("Threads"))
		gridSizer.Add(label_threads, 0, 0, 0)

		self.choice_threads = wx.Choice(self, wx.ID_ANY, choices=["4", "8", "16", "32", "64"])
		self.choice_threads.SetSelection(threads)
		gridSizer.Add(self.choice_threads, 0, 0, 0)

		label_time = wx.StaticText(self, wx.ID_ANY, _("Wait time between scans"))
		gridSizer.Add(label_time, 0, 0, 0)

		self.choice_time = wx.Choice(self, wx.ID_ANY, choices=[
			_("1 minute"), _("2 minutes"), _("3 minutes"), _("4 minutes"), _("5 minutes"), _("10 minutes"), _("15 minutes"), _("30 minutes")])
		self.choice_time.SetSelection(timelapse)
		gridSizer.Add(self.choice_time, 0, 0, 0)

		self.checkbox = wx.CheckBox(self, wx.ID_ANY, _("Sound efects"))
		self.checkbox.SetValue(soundEfects)
		mainSizer.Add(self.checkbox, 0, 0, 0)

		buttonsSizer = wx.StdDialogButtonSizer()
		mainSizer.Add(buttonsSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 4)

		self.button_OK = wx.Button(self, wx.ID_OK, _("OK"))
		self.button_OK.SetDefault()
		buttonsSizer.AddButton(self.button_OK)

		self.button_CANCEL = wx.Button(self, wx.ID_CANCEL, _("Cancel"))
		buttonsSizer.AddButton(self.button_CANCEL)

		buttonsSizer.Realize()

		self.SetSizer(mainSizer)
		mainSizer.Fit(self)

		self.SetAffirmativeId(self.button_OK.GetId())
		self.SetEscapeId(self.button_CANCEL.GetId())

		self.Layout()

		self.Bind(wx.EVT_ACTIVATE, self.onActivate)
		self.Parent.alarm.silence()
		self.Parent.Active = True
		self.Parent.HasDialog = True

	def onActivate(self, event):
		self.Parent.onActivate(event)
		self.Parent.HasDialog = event.Active
		event.Skip()


class PropertiesDialog(wx.Dialog):
	def __init__(self, device, *args, **kwargs):
		kwargs["style"] = kwargs.get("style", 0)
		wx.Dialog.__init__(self, *args, **kwargs)
		self.SetTitle(_("Device properties"))

		sizer = wx.BoxSizer(wx.VERTICAL)

		self.trustRadioBox = wx.RadioBox(self, wx.ID_ANY, _("Trust level"), choices=[_("Red"), _("Yellow"), _("Green")], majorDimension=1, style=wx.RA_SPECIFY_ROWS)
		self.trustRadioBox.SetSelection(0)
		sizer.Add(self.trustRadioBox, 0, 0, 0)

		grid_sizer = wx.GridSizer(4, 2, 1, 1)
		sizer.Add(grid_sizer, 1, wx.EXPAND, 0)

		nameLabel = wx.StaticText(self, wx.ID_ANY, _("Name"))
		grid_sizer.Add(nameLabel, 0, 0, 0)

		self.nameTextEdit = wx.TextCtrl(self, wx.ID_ANY, "")
		grid_sizer.Add(self.nameTextEdit, 0, 0, 0)

		macLabel = wx.StaticText(self, wx.ID_ANY, _("MAC address"))
		grid_sizer.Add(macLabel, 0, 0, 0)

		self.macText = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
		grid_sizer.Add(self.macText, 0, 0, 0)

		firstLabel = wx.StaticText(self, wx.ID_ANY, _("First detected"))
		grid_sizer.Add(firstLabel, 0, 0, 0)

		self.firstText = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
		grid_sizer.Add(self.firstText, 0, 0, 0)

		lastLabel = wx.StaticText(self, wx.ID_ANY, _("Last detected"))
		grid_sizer.Add(lastLabel, 0, 0, 0)

		self.lastText = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
		grid_sizer.Add(self.lastText, 0, 0, 0)

		sizer_button = wx.StdDialogButtonSizer()
		sizer.Add(sizer_button, 0, wx.ALIGN_RIGHT | wx.ALL, 4)

		self.button_OK = wx.Button(self, wx.ID_OK, _("&Save"))
		self.button_OK.SetDefault()
		sizer_button.AddButton(self.button_OK)

		self.SetEscapeId(0xFF)

		sizer_button.Realize()

		self.SetSizer(sizer)
		sizer.Fit(self)

		self.Layout()
		self.Centre()
		name, trust, firstDate, lastDate = self.Parent.scanner.devices[device]
		self.trustRadioBox.SetSelection(trust)
		self.nameTextEdit.SetValue(name)
		self.macText.SetValue(device)
		def date(timestamp):
			dt = datetime.fromtimestamp(timestamp)
			return _("{day}/{month}/{year} {hour}:{minute}").format(
				day=dt.day,
				month=dt.month,
				year=dt.year,
				hour=dt.hour,
				minute=dt.minute
			)
		self.firstText.SetValue(date(firstDate))
		self.lastText.SetValue(date(lastDate))
		self.nameTextEdit.SetFocus()
		self.Bind(wx.EVT_ACTIVATE, self.onActivate)
		self.Parent.alarm.silence()
		self.Parent.Active = True
		self.Parent.HasDialog = True

	def onActivate(self, evt):
		self.Parent.onActivate(evt)
		self.Parent.HasDialog = evt.Active
		evt.Skip()


class NetScannerFrame(wx.Frame):
	def __init__(self, *args, scanner=None, settings=None, alarm=None, **kwargs):

		kwargs["style"] = kwargs.get("style", 0) | wx.CAPTION | wx.MINIMIZE_BOX | wx.STAY_ON_TOP
		wx.Frame.__init__(self, *args, **kwargs)
		self.SetSize((1200, 800))
		self.SetTitle(_("NET Guard"))
		self.Enable(False)
		self.Hide()

		self.frame_menubar = wx.MenuBar()
		menu = wx.Menu()
		item = menu.Append(wx.ID_ANY, _("Settings..."), "")
		self.Bind(wx.EVT_MENU, self.onMenuSettings, item)
		item = menu.Append(wx.ID_ANY, _("Minimize to tray"), "")
		self.Bind(wx.EVT_MENU, self.onMinimize, item)
		item = menu.Append(wx.ID_ANY, _("Stop and close"), "")
		self.Bind(wx.EVT_MENU, self.onClose, item)
		self.frame_menubar.Append(menu, _("File"))
		self.SetMenuBar(self.frame_menubar)

		self.frame_statusbar = self.CreateStatusBar(2)
		self.frame_statusbar.SetStatusWidths([300, 300])
		frame_statusbar_fields = [_("Devices"), _("Scanning...")]
		for i in range(len(frame_statusbar_fields)):
			self.frame_statusbar.SetStatusText(frame_statusbar_fields[i], i)

		self.mainPanel = wx.Panel(self, wx.ID_ANY)

		MainSizer = wx.BoxSizer(wx.HORIZONTAL)

		self.notebook = wx.Notebook(self.mainPanel, wx.ID_ANY)
		MainSizer.Add(self.notebook, 1, wx.EXPAND, 0)

		self.notebook_pane_1 = wx.Panel(self.notebook, wx.ID_ANY)
		self.notebook.AddPage(self.notebook_pane_1, _("online devices"))

		sizer_1 = wx.BoxSizer(wx.VERTICAL)

		self.ARP_list = wx.ListCtrl(self.notebook_pane_1, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
		self.ARP_list.AppendColumn(_("MAC address"), format=wx.LIST_FORMAT_LEFT, width=-1)
		self.ARP_list.AppendColumn(_("IP address"), format=wx.LIST_FORMAT_LEFT, width=-1)
		self.ARP_list.AppendColumn(_("Trust level"), format=wx.LIST_FORMAT_LEFT, width=-1)
		self.ARP_list.AppendColumn(_("Name"), format=wx.LIST_FORMAT_LEFT, width=-1)
		sizer_1.Add(self.ARP_list, 1, wx.EXPAND, 0)

		self.notebook_pane_2 = wx.Panel(self.notebook, wx.ID_ANY)
		self.notebook.AddPage(self.notebook_pane_2, _("all devices"))

		sizer_2 = wx.BoxSizer(wx.VERTICAL)

		self.devices_list = wx.ListCtrl(self.notebook_pane_2, wx.ID_ANY, style=wx.LC_HRULES | wx.LC_REPORT | wx.LC_VRULES)
		self.devices_list.AppendColumn(_("MAC address"), format=wx.LIST_FORMAT_LEFT, width=-1)
		self.devices_list.AppendColumn(_("First detection"), format=wx.LIST_FORMAT_LEFT, width=-1)
		self.devices_list.AppendColumn(_("Last detection"), format=wx.LIST_FORMAT_LEFT, width=-1)
		self.devices_list.AppendColumn(_("Trust level"), format=wx.LIST_FORMAT_LEFT, width=-1)
		self.devices_list.AppendColumn(_("Name"), format=wx.LIST_FORMAT_LEFT, width=-1)
		sizer_2.Add(self.devices_list, 1, wx.EXPAND, 0)

		self.notebook_pane_2.SetSizer(sizer_2)

		self.notebook_pane_1.SetSizer(sizer_1)

		self.mainPanel.SetSizer(MainSizer)

		self.Layout()
		self.Centre()

		self.taskbar_icon = TBIcon(self)
		self.scanner = scanner
		self.settings = settings

		self.Bind(EVT_DEVICE_FOUND, self.onScannerFoundNewDevice)
		self.Bind(EVT_UNTRUSTED_DEVICE_ALERT, self.onUntrustedDeviceFound)
		self.Bind(EVT_SCAN_CYCLE_START, self.onScannerStartCycle)
		self.Bind(EVT_SCAN_CYCLE_FINISH, self.onScannerCycleFinished)
		self.scanner.bind(self.GetEventHandler())
		self.scanner.start()

		self.alarm = alarm
		self.alarm.setDaemon(True)
		self.alarm.start()

		self.ARP_list.SetColumnsOrder([3,1,0,2])
		self.devices_list.SetColumnsOrder([4, 0,1,2,3])
		self.ARP_list.SetFocus()

		self.Bind(wx.EVT_CHAR_HOOK, self.onKey)
		self.Bind(wx.EVT_ACTIVATE, self.onActivate)
		self.Bind(wx.EVT_CLOSE, self.onMinimize)

		self.Active = False
		self.HasDialog = False

		self.RegisterHotKey(999, self.settings["hotkey"]["modifiers"], self.settings["hotkey"]["mainKey"])
		self.Bind(wx.EVT_HOTKEY, self.handleHotKey, id=999)

	def handleHotKey(self, event):
		self.restore()
		event.Skip()

	def onActivate(self, event):
		self.Active = event.Active
		if self.Active: self.alarm.silence()
		event.Skip()

	def onClose(self, event):
		self.scanner.kill()
		self.alarm.kill()
		self.UnregisterHotKey(999)
		self.taskbar_icon.RemoveIcon()
		self.taskbar_icon.Destroy()
		self.closeDialogs()
		self.Unbind(wx.EVT_CLOSE)
		self.Close()

	def closeDialogs(self):
		dialogs = filter(lambda o: isinstance(o, wx.Dialog), self.Children)
		while True:
			try:
				next(dialogs).Close()
			except:
				break

	def onMinimize(self, event):
		self.closeDialogs()
		self.Hide()
		event.Skip()

	def onScannerFoundNewDevice(self, event):
		self.update()
		self.playSound("detection.wav")

	def playSound(self, wavFile):
		if self.settings["soundEfects"] and self.Active and not self.HasDialog:
			f = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "sounds", wavFile)
			if os.path.exists(f):
				Thread(target=winsound.PlaySound,args=(f, winsound.SND_FILENAME)).start()

	def onUntrustedDeviceFound(self, event):
		if not self.Active:
			self.alarm.sound(5.0)

	def onScannerStartCycle(self, event):
		self.frame_statusbar.SetStatusText(_("scan in progress."), 1)

	def onScannerCycleFinished(self, event):
		self.playSound("cycle.wav")
		t = datetime.fromtimestamp(time()+self.scanner.timelapse)
		status = _("Finished. Next scan at {h}:{m}").format(h=t.hour, m=t.minute)
		self.frame_statusbar.SetStatusText(status, 1)

	def update(self):
		status = _("{online} devices online, {registered} registered.").format(
			online = len(self.scanner.arp),
			registered = len(self.scanner.devices)
		)
		self.frame_statusbar.SetStatusText(status, 0)
		oldFocusedItem = self.getMacFromList()
		self.ARP_list.DeleteAllItems()
		for ip, mac in self.scanner.arp:
			self.ARP_list.Append([
				mac,
				ip,
				(_("Red"), _("Yellow"), _("Green"))[self.scanner.devices[mac][DEVICE_INFO_TRUST_LEVEL]],
				self.scanner.devices[mac][DEVICE_INFO_NAME]
			])
		self.devices_list.DeleteAllItems()
		for mac in self.scanner.devices:
			device_name, device_reliability, device_first, device_last = self.scanner.devices[mac]
			self.devices_list.Append([
				mac,
				self.timedelta(device_first),
				self.timedelta(device_last),
				(_("Red"), _("Yellow"), _("Green"))[device_reliability],
				device_name
			])
		if oldFocusedItem:
			if self.ARP_list.HasFocus():
				self.ARP_list.Focus(self.ARP_list.FindItem(-1, oldFocusedItem))
			if self.devices_list.HasFocus():
				self.devices_list.Focus(self.devices_list.FindItem(-1, oldFocusedItem))

	def onKey(self, event):
		def hotkey(code, control=False, shift=False, alt=False):
			return event.GetKeyCode() == code and event.controlDown == control and event.shiftDown == shift and event.altDown == alt
		if hotkey(27):  # escape
			self.onMinimize(event)
		if hotkey(13):  # Enter
			mac = self.getMacFromList()
			if mac:
				dlg = PropertiesDialog(mac, self, wx.ID_ANY)
				dlg.ShowModal()
				self.scanner.updateDevices(mac, name=dlg.nameTextEdit.GetValue(), trustLevel=dlg.trustRadioBox.GetSelection(), save=True)
				dlg.Destroy()
				self.update()
		if hotkey(67, True):  # control+C
			mac = self.getMacFromList()
			if mac:
				pyperclip.copy(mac)
		if hotkey(344):  # F5
			self.scanner.flagWait = False
		event.Skip()

	def getMacFromList(self):
		mac = None
		if self.ARP_list.HasFocus() and self.ARP_list.ItemCount>0:
			row = self.ARP_list.GetFocusedItem()
			if row >= 0:
				mac = self.ARP_list.GetItemText(
					item=row,
					col=0
				)
		elif self.devices_list.HasFocus() and self.devices_list.ItemCount>0:
			row = self.devices_list.GetFocusedItem()
			if row >= 0:
				mac = self.devices_list.GetItemText(
					item=row,
					col=0
				)
		return mac

	def timedelta(self, t):
		td = timedelta(seconds=time()-t)
		if td.days:
			if td.days <21: return _("{} days ago").format(td.days)
			if td.days <63: return _("{} weeks ago").format(td.days//7)
			if td.days < 366: return _("{} months ago").format(td.days//30)
			return _("{} years ago").format(td.days//365)
		if td.seconds <= 60: return _("Now")
		if td.seconds <= 120: return _("1 minute ago")
		if td.seconds <= 60*60: return _("{} minutes ago").format(td.seconds//60)
		return _("{} hours ago").format(td.seconds//3600)

	def restore(self):
		self.Enable(True)
		self.Show()
		self.Center()

	def onMenuSettings(self, event):  # wxGlade: NetScannerFrame.<event_handler>
		lThreads = (4,8,16,32,64)
		lTimelapse = (60,120,180,240,300,600,900,1800)
		dlg = SettingsDialog(self,
			threads=lThreads.index(self.settings["threads"]),
			timelapse=lTimelapse.index(self.settings["timelapse"]),
			soundEfects = self.settings["soundEfects"]
		)
		if dlg.ShowModal() == wx.ID_OK:
			self.settings["threads"] = lThreads[dlg.choice_threads.GetSelection()]
			self.settings["timelapse"] = lTimelapse[dlg.choice_time.GetSelection()]
			self.settings["soundEfects"] = dlg.checkbox.GetValue()
			self.settings.save()
			self.scanner.threads = self.settings["threads"]
			self.scanner.timelapse = self.settings["timelapse"]
		dlg.Destroy()
		event.Skip()


class TBIcon(wx.adv.TaskBarIcon):
	def __init__(self, frame):
		super().__init__()

		self.App = wx.GetApp()
		self.frame = frame

		self.SetIcon(wx.Icon(self.App.IconFile), self.App.Name)

		self.Bind(wx.adv.EVT_TASKBAR_LEFT_UP, self.onIconMenu)
		self.Bind(wx.adv.EVT_TASKBAR_RIGHT_UP, self.onIconMenu)
		self.Bind(wx.adv.EVT_TASKBAR_LEFT_DCLICK, self.onRestore)
		self.Bind(wx.adv.EVT_TASKBAR_RIGHT_DCLICK, self.onRestore)

	def onIconMenu(self, event):
		menu = wx.Menu()
		if self.frame.IsShown():
			caption = _("Hide window")
		else:
			caption = _("Restore")
		restoreItem = menu.Append(wx.ID_ANY, caption)
		menu.Bind(wx.EVT_MENU, self.onRestore, restoreItem)
		settingsItem = menu.Append(wx.ID_ANY, _("Settings"))
		menu.Bind(wx.EVT_MENU, self.onSettings, settingsItem)
		settingsItem .Enable(
			not(True in [isinstance(child, wx.Dialog) for child in self.frame.Children])
		)
		closeItem = menu.Append(wx.ID_ANY, _("Stop and close"))
		menu.Bind(wx.EVT_MENU, self.onClose, closeItem)
		self.PopupMenu(menu)
		menu.Destroy()

	def onRestore(self, event):
		if self.frame.IsShown():
			self.frame.onMinimize(event)
		else:
			self.frame.restore()

	def onSettings(self, event):
		self.frame.onMenuSettings(event)

	def onClose(self, event):
		self.frame.onClose(event)

lancode = locale.normalize(locale.getdefaultlocale()[0].split("_")[0]).split("_")[0]
if gettext.find("netguard", localedir="locale", languages=[lancode]):
	language = gettext.translation("netguard", localedir="locale", languages=[lancode])
	language.install()
	_ = language.gettext
else:
	_ = gettext.gettext
