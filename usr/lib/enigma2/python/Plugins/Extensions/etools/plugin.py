# -*- coding: utf-8 -*-
# 2boom's E-TOOLS
# Copyright (c) 2boom 2011-22
# v.1.2-r11
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
from Screens.Screen import Screen
from Screens.PluginBrowser import PluginBrowser
from Screens.Console import Console
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Screens.Mute import Mute as iMute
from ServiceReference import ServiceReference
from Components.Language import language
from Components.ScrollLabel import ScrollLabel
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ServiceList import ServiceList, refreshServiceList
from Components.PluginComponent import plugins
from Components.config import config, getConfigListEntry, ConfigText, ConfigPassword, ConfigClock, ConfigInteger, ConfigDateTime, ConfigSelection, ConfigSubsection, ConfigSelectionNumber, ConfigYesNo, configfile, NoSave
from Components.ConfigList import ConfigListScreen
from Components.Harddisk import harddiskmanager
from Components.NimManager import nimmanager
from Components.Console import Console as iConsole
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Sources.List import List
from Plugins.Plugin import PluginDescriptor
from GlobalActions import globalActionMap
from keymapparser import readKeymap, removeKeymap
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import fileExists, pathExists, resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
from enigma import eTimer, eServiceReference, eDVBVolumecontrol, eDVBDB, getDesktop, eGetEnigmaDebugLvl
from fcntl import ioctl
from os import environ
import os
import gettext
import time
import enigma

if fileExists(resolveFilename(SCOPE_PLUGINS, "Extensions/AlternativeSoftCamManager/plugin.py")):
	from Plugins.Extensions.AlternativeSoftCamManager.Softcam import getcamcmd

lang = language.getLanguage()
environ["LANGUAGE"] = lang[:2]
gettext.bindtextdomain("enigma2", resolveFilename(SCOPE_LANGUAGE))
gettext.textdomain("enigma2")
gettext.bindtextdomain("etools", "%s%s" % (resolveFilename(SCOPE_PLUGINS), "Extensions/etools/locale/"))

def _(txt):
	t = gettext.dgettext("etools", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

def logging(line):
	log_file = open('/tmp/etools.log', 'a')
	log_file.write(line)
	log_file.close()

def isSwapRunInfo():
	if fileExists('/proc/swaps'):
		for line in open('/proc/swaps'):
			if 'swapfile' in line:
				return "%s %dMb" % (line.split()[0].replace('/swapfile', ''), round(int(line.split()[2]) / 1024 + (0.5 if int(line.split()[2]) / 1024 > 0 else -0.5)))
	else:
		return "Swap is off"
		
def status_path():
	statusfile = ['/var/lib/opkg/status', '/usr/lib/ipkg/status', '/var/opkg/status']
	for i in range(len(statusfile)):
		if fileExists('%s.tmp' % statusfile[i]):
			enigma.eConsoleAppContainer().execute('mv %s.tmp %s' % (statusfile[i], statusfile[i]))
	for i in range(len(statusfile)):
		if fileExists(statusfile[i]):
			return statusfile[i]
	return statusfile[0]
	
def mountp():
	pathmp = ['/usr/share/enigma2/', '/etc/enigma2/', '/tmp/']
	if os.path.isfile('/proc/mounts'):
		for line in open('/proc/mounts'):
			if line.startswith(('/dev/sd', '/dev/disk/by-uuid/', '/dev/mmc', '/dev/mtdblock')) and ' / ' not in line:
				pathmp.append(line.split()[1].replace('\\040', ' ') + '/')
	return pathmp

def mountpcrash():
	pathmp = ['/home/root/', '/home/root/logs/', '/tmp/', ]
	for p in harddiskmanager.getMountedPartitions():
		if os.path.exists(p.mountpoint):
			if p.mountpoint != '/':
				pathmp.append('%s/' % p.mountpoint)
	return pathmp

def remove_line(filename, what):
	if fileExists(filename):
		file_read = open(filename).readlines()
		file_write = open(filename, 'w')
		for line in file_read:
			if what not in line:
				file_write.write(line)
		file_write.close()
		
def copyfile(filename, writename):
	if fileExists(filename):
		file_read = open(filename).readlines()
		file_write = open(writename, 'w')
		for line in file_read:
			file_write.write(line)
		file_write.close()
		
def add_line(filename, what):
	if os.path.isfile(filename):
		with open(filename, 'a') as file_out:
			file_out.write(what)
			file_out.close()

def cronpath():
	path = ['/etc/cron/crontabs/root', '/etc/cron/crontabs', '/etc/bhcron', '/etc/crontabs/root', '/var/spool/cron/crontabs/root']
	for i in range(len(path)):
		if fileExists(path[i]):
			return path[i]
	return path[0]
	
def cronedit_data(what):
	DATA = []
	for i in range(what):
		DATA.append((str(i), str(i)))
	DATA[0] = ('*', '*')
	return DATA

TIMEMIN = [
		('0', _("Off")),
		('15', _("15 min")),
		('30', _("30 min")),
		('45', _("45 min")),
		('1', _("60 min")),
		('2', _("120 min")),
		('3', _("180 min")),
		]
FEEDFILTER = [
		("0", _("Off")),
		("firmware-", _("firmware")),
		("enigma2-plugin-", _("enigma2-plugin")),
		("enigma2-plugin-drivers-", _("enigma2-plugin-drivers")),
		("enigma2-plugin-extensions-", _("enigma2-plugin-extensions")),
		("enigma2-plugin-picons-", _("enigma2-plugin-picons")),
		("enigma2-plugin-settings-", _("enigma2-plugin-settings")),
		("enigma2-plugin-skins-", _("enigma2-plugin-skins")),
		("enigma2-plugin-softcams-", _("enigma2-plugin-softcams")),
		("enigma2-plugin-systemplugins-", _("enigma2-plugin-systemplugins")),
		("kernel-firmware", _("kernel-firmware")),
		("kernel-module", _("kernel-module")),
		("python", _("python")),
		("lib", _("library")),
		]

KEYS = [("0", "Off"),
		("KEY_TEXT", "TEXT"),
		("KEY_SUBTITLE", "SUBTITLE"),
		("KEY_HELP", "HELP"),
		("KEY_RED", "LONG_RED"),
		("KEY_GREEN", "LONG_GREEN"),
		("KEY_YELLOW", "LONG_YELLOW"),
		("KEY_BLUE", "LONG_BLUE"),]
		
NTPSERVER = [
		("pool.ntp.org", _("default")),
		("amazon.pool.ntp.org", _("Amazon NTP")),
		("time.google.com", _("Google Public NTP")),
		("time.cloudflare.com", _("Cloudflare NTP")),
		("time.facebook.com", _("Facebook NTP")),
		("time.windows.com", _("Microsoft NTP")),]
		
FORCECOMMAND = ["--force-reinstall", "--force-overwrite", "--force-downgrade"]

FORCEREMOVE = ["one remove", "all remove"]

FEEDFILTERQ = [
		"0", "firmware-", "enigma2-plugin-", "enigma2-plugin-drivers-", "enigma2-plugin-extensions-",
		"enigma2-plugin-picons-", "enigma2-plugin-settings-", "enigma2-plugin-skins-", "enigma2-plugin-softcams-",
		"enigma2-plugin-systemplugins-", "kernel-firmware", "kernel-module", "python", "lib"
		]
		
DNSLIST = [
			(0, _("Off"), ' ', ' '),
			(1, _("Google DNS"), '8.8.8.8', '8.8.4.4'),
			(2, _("Quad9 DNS"), '9.9.9.9', '149.112.112.112'),
			(3, _("Cloudflare DNS"), '1.1.1.1', '1.0.0.1'),
			(4, _("AdGuard DNS"), '94.140.14.14', '94.140.15.15'),
		]
		
USERBQ = ["Lamedb & Userbouquets", "Lamedb", "Userbouquets"]

config.plugins.etools = ConfigSubsection()
config.plugins.etools.showmain = ConfigYesNo(default = False)
config.plugins.etools.sysupext = ConfigYesNo(default = False)
config.plugins.etools.menuhighlighticon = ConfigYesNo(default = False)
config.plugins.etools.showemmenu = ConfigYesNo(default = False)
config.plugins.etools.showeconfig = ConfigYesNo(default = False)
config.plugins.etools.pluginbrext = ConfigYesNo(default = False)
config.plugins.etools.crash = ConfigYesNo(default = False)
config.plugins.etools.needrestarte2 = ConfigYesNo(default = False)
config.plugins.etools.showsetupipk = ConfigYesNo(default = False)
config.plugins.etools.ext = ConfigYesNo(default = False)
config.plugins.etools.hdmiin = ConfigYesNo(default = False)
config.plugins.etools.extrestart = ConfigYesNo(default = False)
config.plugins.etools.extswitch = ConfigYesNo(default = False)
config.plugins.etools.needrestartemu = ConfigYesNo(default = True)
config.plugins.etools.showscript = ConfigYesNo(default = False)
config.plugins.etools.reloadbouquets = ConfigYesNo(default = False)
config.plugins.etools.ac3dmixext = ConfigYesNo(default = False)
config.plugins.etools.restartmute = ConfigYesNo(default = False)
config.plugins.etools.restartcount = ConfigInteger(default = 0)
config.plugins.etools.dnsname = ConfigSelection(default = 0, choices = DNSLIST)
config.plugins.etools.keyhdmiin = ConfigSelection(default = "0", choices = KEYS)
config.plugins.etools.keyac3dmx = ConfigSelection(default = "0", choices = KEYS)
config.plugins.etools.keyreloadbq = ConfigSelection(default = "0", choices = KEYS)
config.plugins.etools.keyrestaremu = ConfigSelection(default = "0", choices = KEYS)
config.plugins.etools.keyrestartenigma = ConfigSelection(default = "0", choices = KEYS)
config.plugins.etools.keyemuswitch = ConfigSelection(default = "0", choices = KEYS)
config.plugins.etools.ntpserver = ConfigSelection(default = "pool.ntp.org", choices = NTPSERVER)
config.plugins.etools.ntponoff = ConfigSelection(default = "0", choices = TIMEMIN)
config.plugins.etools.filtername = ConfigSelection(default = "0", choices = FEEDFILTER)
config.plugins.etools.filterrm = ConfigSelection(default = "0", choices = FEEDFILTER)
config.plugins.etools.filterdw = ConfigSelection(default = "0", choices = FEEDFILTER)
config.plugins.etools.activeemu = ConfigText(default = _("None"))
config.plugins.etools.hdmiinonoff = ConfigText(default = _("On"))
config.plugins.etools.ac3state  = ConfigText(default = _("On"))
config.plugins.etools.userdir = ConfigText(default="/", visible_width = 70, fixed_size = False)
config.plugins.etools.epgname = ConfigText(default='epg.dat', visible_width = 70, fixed_size = False)
config.plugins.etools.command = ConfigText(default="/usr/bin/", visible_width = 70, fixed_size = False)
config.plugins.etools.direct = ConfigSelection(choices = mountp())
config.plugins.etools.crashpath = ConfigSelection(choices = mountpcrash())
config.plugins.etools.systeminfomode = ConfigSelection(default = "Short", choices = [
		("Short", _("Short")),
		("Full", _("Full")),
])
config.plugins.etools.crashremmode = ConfigSelection(default = "one remove", choices = [
		("one remove", _("one remove")),
		("all remove", _("all remove")),
])
config.plugins.etools.scriptpath = ConfigSelection(default = "/tmp/", choices = [
		("/usr/script/", _("/usr/script/")),
		("/tmp/", _("/tmp/")),
])
config.plugins.etools.showplugin = ConfigSelection(default = "Config", choices = [
		("Config", _("Config")),
		("Menu", _("Menu")),
])
config.plugins.etools.multifilemode = ConfigSelection(default = "Multi", choices = [
		("Multi", _("Multi files")),
		("Single", _("Single file")),
])
config.plugins.etools.force = ConfigSelection(default = "--force-reinstall", choices = [
		("--force-reinstall", _("--force-reinstall")),
		("--force-overwrite", _("--force-overwrite")),
		("--force-downgrade", _("--force-downgrade")),
])
config.plugins.etools.reloads = ConfigSelection(default = "0", choices = [
		("0", _("Lamedb & Userbouquets")),
		("1", _("Lamedb")),
		("2", _("Userbouquets")),
		])
config.plugins.etools.droptime = ConfigSelection(default = '0', choices = TIMEMIN)
config.plugins.etools.opkg = ConfigSelection(default = '0', choices = TIMEMIN)
config.plugins.etools.dropmode = ConfigSelection(default = '1', choices = [
		('1', _("free pagecache")),
		('2', _("free dentries and inodes")),
		('3', _("free pagecache, dentries and inodes")),
		])
config.plugins.etools.min = NoSave(ConfigSelection(default = '*', choices = cronedit_data(60)))
config.plugins.etools.hour = NoSave(ConfigSelection(default = '*', choices = cronedit_data(24)))
config.plugins.etools.dayofmonth = NoSave(ConfigSelection(default = '*', choices = cronedit_data(32)))
config.plugins.etools.month = NoSave(ConfigSelection(default = "*", choices = [
		("*", "*"),
		("1", _("January")),
		("2", _("February")),
		("3", _("March")),
		("4", _("April")),
		("5", _("May")),
		("6", _("June")),
		("7", _("Jule")),
		("8", _("August")),
		("9", _("September")),
		("10", _("October")),
		("11", _("November")),
		("12", _("December")),
		]))
config.plugins.etools.dayofweek = NoSave(ConfigSelection(default = "*", choices = [
		("*", "*"),
		("0", _("Sunday")),
		("1", _("Monday")),
		("2", _("Tuesday")),
		("3", _("Wensday")),
		("4", _("Thursday")),
		("5", _("Friday")),
		("6", _("Saterday")),
		]))
config.plugins.etools.every = NoSave(ConfigSelection(default = "0", choices = [
		("0", _("No")),
		("1", _("Minute")),
		("2", _("Hour")),
		("3", _("Day of month")),
		("4", _("Month")),
		("5", _("Day of week")),
		]))
######################################################################################
def ecm_view():
	list = ''
	port = False
	linecaid = ['caid:', 'provider:', 'provid:', 'pid:', 'hops:', 'system:', 'address:', 'using:', 'ecm time:']
	linefrom = ['from:', 'protocol:', 'caid:', 'pid:', 'reader:', 'hops:', 'system:', 'Service:', 'CAID:', 'Provider:']
	if fileExists("/tmp/ecm.info"):
		try:
			ecmfiles = open('/tmp/ecm.info', 'r')
			for line in ecmfiles:
				if 'port:' in line: 
					port = True
				for i in range(len(linecaid)):
					if linecaid[i] in line:
						line = line.replace(' ','').replace(':',': ')
				for i in range(len(linefrom)):
					if linefrom[i] in line:
						line = '%s  ' % line.strip('\n')
				if 'Signature' in line:
					line = ""
				if '=' in line:
					line = '%s, ' % line.lstrip('=').replace('======', "").replace('\n', "").rstrip()
				if 'ecmtime:' in line:
					line = line.replace('ecmtime:', 'ecm time:')
				if 'response time:' in line:
					line = line.replace('response time:', 'ecm time:').replace('decoded by', 'by')
				if not line.startswith('\n'): 
					if 'protocol:' in line and port == False:
						line = '\n%s' % line
					if 'pkey:' in line:
						line = '\n%s\n' % line 
					list += line
			ecmfiles.close()
			return list
		except:
			return ''
	return ''
######################################################################################
SKIN_MAINMENU = """
<screen name="etoolsmainmenu"  position="center,220" size="1125,610" title="">
	<ePixmap position="20,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/green.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_green" render="Label" position="273,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="menu" render="Listbox" position="26,10" size="1080,525" scrollbarMode="showOnDemand">
		<convert type="TemplatedMultiContent">
			{"template": [
				MultiContentEntryText(pos = (105, 5), size = (975, 38), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
				MultiContentEntryText(pos = (123, 44), size = (945, 30), font=1, flags = RT_HALIGN_LEFT, text = 2), # index 3 is the Description
				MultiContentEntryPixmapAlphaTest(pos = (7, 7), size = (75, 60), png = 3), # index 4 is the pixmap
				],
			"fonts": [gFont("Regular", 32),gFont("Regular", 23)],
			"itemHeight": 75
			}
		</convert>
	</widget>
</screen>"""
######################################################################################
class etoolsmainmenu(Screen):
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.skin = SKIN_MAINMENU
		self.setTitle(_("E-Tools"))
		self.indexpos = None
		self.onepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/e-tools.png"))
		self.curpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/e-toolsa.png"))
		if config.plugins.etools.menuhighlighticon.value:
			BKEYS = {
					"ok": self.keyOK,
					"cancel": self.cancel,
					"back": self.cancel,
					"red": self.cancel,
					"green": self.keyGreen,
					"info": self.sysInfo,
					"down": self.keyDown,
					"up": self.keyUp,
					"left": self.pageUp,
					"right": self.pageDown,
					"1": self.go,
					"2": self.go,
					"3": self.go,
					"4": self.go,
					"5": self.go,
					"6": self.go,
					"7": self.go,
					"8": self.go,
					"9": self.go,
					"0": self.go
					}
		else:
			BKEYS = {
					"ok": self.keyOK,
					"cancel": self.cancel,
					"back": self.cancel,
					"red": self.cancel,
					"green": self.keyGreen,
					"info": self.sysInfo,
					"1": self.go,
					"2": self.go,
					"3": self.go,
					"4": self.go,
					"5": self.go,
					"6": self.go,
					"7": self.go,
					"8": self.go,
					"9": self.go,
					"0": self.go
					}
		self["shortcuts"] = NumberActionMap(["ShortcutActions", "WizardActions", "NumberActions", "EPGSelectActions", "EventViewActions", "SetupActions"], BKEYS, -1)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Config"))
		self.list = []
		self["menu"] = List(self.list)
		self.mainmenu()
		
	def sysInfo(self):
		self.session.open(Aboutsystem)

	def mainmenu(self):
		self.list = []
		if config.plugins.etools.menuhighlighticon.value:
			self.list.append((_("E-Softcam manager (%s)" % config.plugins.etools.activeemu.value.split()[0]), 1, _("Start, stop, restart softcam"), self.curpng))
		else:
			self.list.append((_("E-Softcam manager (%s)" % config.plugins.etools.activeemu.value.split()[0]), 1, _("Start, stop, restart softcam"), self.onepng))
		self.list.append((_("E-Installer (%s mode)" % config.plugins.etools.multifilemode.value), 2, _("Install/uninstall local .ipk & .tar.gz"), self.onepng ))
		self.list.append((_("E-Remover for packets"), 3, _("Local remove ipk packets"), self.onepng ))
		self.list.append((_("E-Feed Installer"), 4, _("Install extensions from feed"), self.onepng ))
		self.list.append((_("E-Feed Downloader"), 5, _("Download extensions from feed"), self.onepng ))
		self.list.append((_("E-Crash viewer (%s)" % config.plugins.etools.crashpath.value.rstrip('/')), 6, _("Enigma2 crashlog viewer"), self.onepng ))
		self.list.append((_("E-Swap manager (%s)" % isSwapRunInfo()), 7, _("Create, start, stop, remove swapfile"), self.onepng ))
		self.list.append((_("E-Script (%s)" % config.plugins.etools.scriptpath.value.rstrip('/')), 8, _("Start script files from user directory"), self.onepng))
		self.list.append((_("E-Cron editor" ), 9, _("Add, remove tabs"), self.onepng ))
		self.list.append((_("E-Kernel module manager" ), 10, _("Load/unload kernel module"), self.onepng ))
		self.list.append((_("E-System upgrade" ), 11, _("Selective or full system upgrade"), self.onepng ))
		if self.indexpos != None:
			self["menu"].setIndex(self.indexpos)
		self["menu"].setList(self.list)
		
	def go(self, num = None):
		if num is not None:
			num -= 1
			if not num < self["menu"].count():
				return
			self["menu"].setIndex(num)
		item = self["menu"].getCurrent()[1]
		self.select_item(item)
		
	def keyOK(self, item = None):
		self.indexpos = self["menu"].getIndex()
		if item == None:
			item = self["menu"].getCurrent()[1]
			self.select_item(item)

	def select_item(self, item):
		if item:
			if item == 1:
				self.session.open(emuSelelection)
			elif item == 2:
				self.session.open(einstaller)
			elif item == 3:
				self.session.open(eRemoveIPK)
			elif item == 4:
				self.session.open(InstallFeed)
			elif item == 5:
				self.session.open(eDownloadFeed)
			elif item == 6:
				self.session.open(eCrashLogScreen)
			elif item == 7:
				self.session.open(ESwapScreen2)
			elif item == 8:
				self.session.open(EScriptScreen2)
			elif item == 9:
				self.session.open(CrontabMan)
			elif item == 10:
				self.session.open(eKernel)
			elif item == 11:
				self.session.open(eupgrade)
			else:
				self.cancel(None)
				
	def pageDown(self):
		line = self["menu"].getCurrent()
		restore_icon = (line[0], line[1], line[2], self.onepng)
		self["menu"].modifyEntry(self["menu"].getIndex(), restore_icon)
		self["menu"].setIndex(self["menu"].count() - 1)
		line = self["menu"].getCurrent()
		change_icon = (line[0], line[1], line[2], self.curpng)
		self["menu"].modifyEntry(self["menu"].getIndex(), change_icon)
		
	def pageUp(self):
		line = self["menu"].getCurrent()
		restore_icon = (line[0], line[1], line[2], self.onepng)
		self["menu"].modifyEntry(self["menu"].getIndex(), restore_icon)
		self["menu"].setIndex(0)
		line = self["menu"].getCurrent()
		change_icon = (line[0], line[1], line[2], self.curpng)
		self["menu"].modifyEntry(self["menu"].getIndex(), change_icon)
		
	def keyDown(self):
		line = self["menu"].getCurrent()
		restore_icon = (line[0], line[1], line[2], self.onepng)
		self["menu"].modifyEntry(self["menu"].getIndex(), restore_icon)
		if self["menu"].getIndex() + 1 >= self["menu"].count():
			self["menu"].setIndex(0)
			line = self["menu"].getCurrent()
			change_icon = (line[0], line[1], line[2], self.curpng)
			self["menu"].modifyEntry(self["menu"].getIndex(), change_icon)
		else:
			self["menu"].selectNext()
			line = self["menu"].getCurrent()
			change_icon = (line[0], line[1], line[2], self.curpng)
			self["menu"].modifyEntry(self["menu"].getIndex(), change_icon)
			
	def keyUp(self):
		line = self["menu"].getCurrent()
		restore_icon = (line[0], line[1], line[2], self.onepng)
		self["menu"].modifyEntry(self["menu"].getIndex(), restore_icon)
		if self["menu"].getIndex() == 0:
			self["menu"].setIndex(self["menu"].count() - 1)
			line = self["menu"].getCurrent()
			change_icon = (line[0], line[1], line[2], self.curpng)
			self["menu"].modifyEntry(self["menu"].getIndex(), change_icon)
		else:
			self["menu"].selectPrevious()
			line = self["menu"].getCurrent()
			change_icon = (line[0], line[1], line[2], self.curpng)
			self["menu"].modifyEntry(self["menu"].getIndex(), change_icon)
			
	def cancel(self):
		self.close(False)
		
	def keyGreen(self):
		self.session.open(etoolsConfigExtentions2)
######################################################################################
SKIN_CFG = """
<screen name="etoolsConfigExtentions2" position="397,220" size="1125,795" title="">
	<widget position="25,10" size="1080,672" font="Regular;32" itemHeight="48" name="config" scrollbarMode="showOnDemand" />
	<ePixmap position="20,785" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,785" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/green.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,740" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_green" render="Label" position="273,740" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget name="description" position="25,695" size="1080,35" font="Regular;29" transparent="1" valign="top" halign="center" />
</screen>"""
######################################################################################
class etoolsConfigExtentions2(ConfigListScreen, Screen):
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_CFG
		self.setTitle(_("E-Tools config"))
		if config.plugins.etools.needrestarte2.value:
			self.setTitle(_("E-Tools config - Enigma2 will restart"))
		self.path = cronpath()
		self.mapto_key = ['renigma2', 'restemu', 'relbq', 'hdmiin', 'ac3mix', 'eswitch']
		self.config_key = [config.plugins.etools.keyrestartenigma.value, config.plugins.etools.keyrestaremu.value, config.plugins.etools.keyreloadbq.value, config.plugins.etools.keyhdmiin.value, config.plugins.etools.keyac3dmx.value, config.plugins.etools.keyemuswitch.value]
		self.config_files = [config.plugins.etools.dnsname.value, config.plugins.etools.ntponoff.value, config.plugins.etools.ntpserver.value, config.plugins.etools.droptime.value, config.plugins.etools.dropmode.value, config.plugins.etools.opkg.value]
		self.button_map =[]
		self.button_map_after =[]
		for i in range(len(self.mapto_key)):
			self.button_map.append((self.mapto_key[i],self.config_key[i]))
		self.list = []
		self.list.append(getConfigListEntry(_("E-Tools: in Main Menu"), config.plugins.etools.showmain, _("When Enabled E-TOOLS will appear in the main menu")))
		self.list.append(getConfigListEntry(_("E-Tools: MenuMode in Plugins Menu"), config.plugins.etools.showplugin, _("Choosing a view (menu or configuration) in the plugins menu")))
		self.list.append(getConfigListEntry(_("E-Tools: Menu Show in ExtensionMenu"), config.plugins.etools.showemmenu, _("When enabled, the E-TOOLS Menu will appear in the extensions menu")))
		self.list.append(getConfigListEntry(_("E-Tools: System info mode"),config.plugins.etools.systeminfomode, _("When enabled, the E-TOOLS will show full System Info")))
		self.list.append(getConfigListEntry(_("E-Tools: Config Show in ExtensionMenu"), config.plugins.etools.showeconfig, _("When enabled, the E-TOOLS Configuration will appear in the extensions menu")))
		if not self.image_is_atv():
			self.list.append(getConfigListEntry(_("E-Tools: Highlight MainMenu icon"), config.plugins.etools.menuhighlighticon, _("Highligt menu icon work in Openpli only")))
		self.list.append(getConfigListEntry(_("E-Softcam: Show in ExtensionMenu"), config.plugins.etools.ext, _("When enabled, the E-Softcam Manager will appear in the extensions menu")))
		self.list.append(getConfigListEntry(_("E-Softcam Restart: Show in ExtensionMenu"), config.plugins.etools.extrestart, _("When enabled, the E-Softcam Restarter will appear in the extensions menu")))
		self.list.append(getConfigListEntry(_("E-Softcam Restart: Hotkey"), config.plugins.etools.keyrestaremu, _("Choosing a Hotkey for Restart softcam")))
		self.list.append(getConfigListEntry(_("E-Softcam Switch Config: Restart Emu after Switch config"), config.plugins.etools.needrestartemu, _("When enabled, Emu will restart after switch config")))
		self.list.append(getConfigListEntry(_("E-Softcam Switch Config: Show in ExtensionMenu"), config.plugins.etools.extswitch, _("When enabled, the E-Softcam Switch Config will appear in the extensions menu")))
		self.list.append(getConfigListEntry(_("E-Softcam Switch Config: Hotkey"), config.plugins.etools.keyemuswitch, _("Choosing a Hotkey for E-Softcam Switch Config")))
		self.list.append(getConfigListEntry(_("E-Installer: Show in ExtensionMenu"), config.plugins.etools.showsetupipk, _("When enabled, the E-Installer will appear in the extensions menu")))
		self.list.append(getConfigListEntry(_("E-Installer: Select Multi or Single file mode"), config.plugins.etools.multifilemode, _("Mode selection (multiple or single) for installation packages")))
		self.list.append(getConfigListEntry(_("E-Installer: Force install mode"), config.plugins.etools.force, _("Selecting a Mode for Forced Installation of Packages")))
		self.list.append(getConfigListEntry(_("E-Installer: User directory on mount device"), config.plugins.etools.userdir, _("Selecting a directory to search for installation packages")))
		self.list.append(getConfigListEntry(_("E-Remover: Filter extentions"), config.plugins.etools.filterrm, _("Selecting filters to quickly find packages for E-Remover")))
		self.list.append(getConfigListEntry(_("E-Feed Installer: Filter extentions"), config.plugins.etools.filtername, _("Selecting filters to quickly find packages for E-Feed Installer")))
		self.list.append(getConfigListEntry(_("E-Feed Downloder: Filter extentions"), config.plugins.etools.filterdw, _("Selecting filters to quickly find packages for E-Feed Downloder")))
		self.list.append(getConfigListEntry(_("E-System Upgrade: Show in ExtensionMenu"),config.plugins.etools.sysupext, _("When enabled, the E-System Upgrade will appear in the extensions menu")))
		self.list.append(getConfigListEntry(_("E-Crash: Show in ExtensionMenu"), config.plugins.etools.crash, _("When enabled, the E-Crash viewer will appear in the extensions menu")))
		self.list.append(getConfigListEntry(_("E-Crash: Path for crashlog files"), config.plugins.etools.crashpath, _("Selecting path to quickly find crash log files")))
		self.list.append(getConfigListEntry(_("E-Crash: Remove files mode"), config.plugins.etools.crashremmode, _("Selecting a Mode (single or all) for remove crash log files")))
		self.list.append(getConfigListEntry(_("E-Script: Show in ExtensionMenu"), config.plugins.etools.showscript, _("When enabled, the E-Script will appear in the extensions menu")))
		self.list.append(getConfigListEntry(_("E-Script: Path for script files"), config.plugins.etools.scriptpath, _("Selecting path to quickly find script files")))
		self.list.append(getConfigListEntry(_("E-Reload: Show in ExtensionMenu"), config.plugins.etools.reloadbouquets, _("When enabled, the E-Reload will appear in the extensions menu")))
		self.list.append(getConfigListEntry(_("E-Reload: Mode"), config.plugins.etools.reloads, _("Choosing a mode (Lamedb or Userbouquets) for E-Reload")))
		self.list.append(getConfigListEntry(_("E-Reload: Hotkey"), config.plugins.etools.keyreloadbq, _("Choosing a Hotkey for E-Reload")))
		if self.hdmi_in_check():
			self.list.append(getConfigListEntry(_("E-HDMI-IN On/Off: Show in ExtensionMenu"), config.plugins.etools.hdmiin, _("When enabled, the E-HDMI-IN (On/Off) will appear in the extensions menu")))
			self.list.append(getConfigListEntry(_("E-HDMI-IN: Hotkey"), config.plugins.etools.keyhdmiin, _("Choosing a Hotkey for E-HDMI-IN")))
		self.list.append(getConfigListEntry(_("E-AC3,DTS downmix: Show in ExtensionMenu"), config.plugins.etools.ac3dmixext, _("When enabled, the E-AC3,DTS downmix will appear in the extensions menu")))
		self.list.append(getConfigListEntry(_("E-AC3,DTS downmix: Hotkey"), config.plugins.etools.keyac3dmx, _("Choosing a Hotkey for E-AC3,DTS downmix")))
		self.list.append(getConfigListEntry(_("E-Link: Plugin browser in ExtensionMenu"), config.plugins.etools.pluginbrext, _("When enabled, the Plugin browser will appear in the extensions menu")))
		self.list.append(getConfigListEntry(_("E-Hotkey: Enigma2 restart"), config.plugins.etools.keyrestartenigma, _("Choosing a Hotkey for Enigma2 restart")))
		self.list.append(getConfigListEntry(_("E-Hotkey: Mute after Enigma2 restart "), config.plugins.etools.restartmute, _("When Enabled, after Enigma2 restarted sound will be off")))
		self.list.append(getConfigListEntry(_("E-Settings: Autotime cache flush"), config.plugins.etools.droptime, _("Choosing a time for cache flush")))
		self.list.append(getConfigListEntry(_("E-Settings: Set cache flush mode"), config.plugins.etools.dropmode, _("Choosing a mode (free pagecache, dentries and inodes) for cache flush")))
		self.list.append(getConfigListEntry(_("E-Settings: NTP time syncronization"), config.plugins.etools.ntponoff, _("When Enabled NTP time syncronization will on")))
		self.list.append(getConfigListEntry(_("E-Settings: Select NTP server"), config.plugins.etools.ntpserver, _("Choosing a server for NTP time syncronization")))
		self.list.append(getConfigListEntry(_("E-Settings: Add DNS server"), config.plugins.etools.dnsname, _("Choosing and add DNS server")))
		self.list.append(getConfigListEntry(_("E-Settings: Set EPG filename"), config.plugins.etools.epgname, _("Choosing a EPG file name")))
		self.list.append(getConfigListEntry(_("E-Settings: Path to place EPG file"), config.plugins.etools.direct, _("Choosing a path for EPG file")))
		self.list.append(getConfigListEntry(_("E-Settings: Auto opkg update"), config.plugins.etools.opkg, _("Choosing a time for opkg update")))
		ConfigListScreen.__init__(self, self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Save"))
		self["description"] = Label("")
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions", "MovieSelectionActions", "EPGSelectActions", "SetupActions"],
		{
			"red": self.cancel,
			"cancel": self.cancel,
			"green": self.save,
			"info": self.sysInfo,
			"ok": self.save
		}, -2)

	def sysInfo(self):
		self.session.open(Aboutsystem)
			
	def cancel(self):
		if config.plugins.etools.needrestarte2.value:
			config.plugins.etools.needrestarte2.value = False
			config.plugins.etools.needrestarte2.save()
			enigma.eConsoleAppContainer().execute('wget -q -O - http://root@127.0.0.1/web/powerstate?newstate=3')
		self.close(False)
		
		
	def ntpserver(self, what):
		with open('/etc/default/ntpdate', 'w') as ntpconfig:
			ntpconfig.write('# Configuration script used by ntpdate-sync script\n\nNTPSERVERS="%s"\n\n# Set to "yes" to write time to hardware clock on success\nUPDATE_HWCLOCK="no"\n' % what)
			ntpconfig.close()
			
	def cron_ntp(self):
		if config.plugins.etools.ntponoff.value != '0':
			with open(self.path, 'a') as cron_root:
				if config.plugins.etools.ntponoff.value not in ('1', '2', '3'):
					cron_root.write('*/%s * * * * /usr/bin/ntpdate-sync silent\n' % config.plugins.etools.ntponoff.value)
				else:
					cron_root.write('1 */%s * * * /usr/bin/ntpdate-sync silent\n' % config.plugins.etools.ntponoff.value)
				cron_root.close()
			with open('%scron.update' % self.path[:-4], 'w') as cron_update:
				cron_update.write('root')
				cron_update.close()

	def cron_setup(self):
		if config.plugins.etools.droptime.value != '0':
			with open(self.path, 'a') as cron_root:
				if config.plugins.etools.droptime.value not in ('1', '2', '3'):
					cron_root.write('*/%s * * * * echo %s > /proc/sys/vm/drop_caches\n' % (config.plugins.etools.droptime.value, config.plugins.etools.dropmode.value))
				else:
					cron_root.write('1 */%s * * * echo %s > /proc/sys/vm/drop_caches\n' % (config.plugins.etools.droptime.value, config.plugins.etools.dropmode.value))
				cron_root.close()
			with open('%scron.update' % self.path[:-4], 'w') as cron_update:
				cron_update.write('root')
				cron_update.close()
				
	def cron_opkgupdate(self):
		with open(self.path, 'a') as cron_root:
			if config.plugins.etools.opkg.value not in ('1', '2', '3'):
				cron_root.write('*/%s * * * * opkg update\n' % config.plugins.etools.opkg.value)
			else:
				cron_root.write('1 */%s * * * opkg update\n' % config.plugins.etools.opkg.value)
			cron_root.close()
		with open('%scron.update' % self.path[:-4], 'w') as cron_update:
			cron_update.write('root')
			cron_update.close()

	def hdmi_in_check(self):
		if fileExists('/proc/interrupts'):
			for line in open('/proc/interrupts'):
				if line.endswith('HDMI_RX_0\n'):
					return True
		return False
		
	def image_is_atv(self):
		images = ['openatv', 'openhdf', 'openvix', 'opendroid', 'openvision']
		if fileExists('/etc/issue'):
			for line in open('/etc/issue'):
				for i in range(len(images)):
					if images[i] in line.lower():
						return True
		return False
	
	def resolv(self, do):
		DNSIP = []
		for i in range(1, len(DNSLIST)):
			DNSIP.append(DNSLIST[i][-2])
			DNSIP.append(DNSLIST[i][-1])
		if fileExists('/etc/resolv.conf'):
			for i in range(len(DNSIP)):
				remove_line('/etc/resolv.conf', DNSIP[i])
			if do == 'add':
				add_line('/etc/resolv.conf', 'nameserver %s\n' % DNSLIST[config.plugins.etools.dnsname.value][-2])
				add_line('/etc/resolv.conf', 'nameserver %s\n' % DNSLIST[config.plugins.etools.dnsname.value][-1])
			
	def save(self):
		if config.plugins.etools.keyhdmiin.value != "0":
			config.plugins.etools.hdmiin.value = False
		if config.plugins.etools.keyac3dmx.value != "0":
			config.plugins.etools.ac3dmixext.value = False
		if config.plugins.etools.keyreloadbq.value != "0":
			config.plugins.etools.reloadbouquets.value = False
		if config.plugins.etools.keyemuswitch.value != "0":
			config.plugins.etools.extswitch.value = False
		config.plugins.etools.restartcount.value = config.misc.startCounter.value
		config.plugins.etools.restartcount.save()
		config.misc.epgcache_filename.value = '%s%s' % (config.plugins.etools.direct.value, config.plugins.etools.epgname.value)
		config.misc.epgcache_filename.save()
		if not self.image_is_atv():
			config.ntp.server.value = config.plugins.etools.ntpserver.value
			config.ntp.server.save()
			if config.plugins.etools.ext.value:
				config.misc.softcam_setup.extension_menu.value = False
			else:
				config.misc.softcam_setup.extension_menu.value = True
			config.misc.softcam_setup.extension_menu.save()
		else:
			config.misc.SyncTimeUsing.value = 1
			config.misc.useNTPminutes.value = int(config.plugins.etools.ntponoff.value)
			config.plugins.etools.menuhighlighticon.value = False
			config.plugins.etools.menuhighlighticon.save()
			config.misc.SyncTimeUsing.save()
			config.misc.useNTPminutes.save()
			
		if not fileExists(self.path):
			open(self.path, 'a').close()
		for i in self["config"].list:
			if len(i) > 1:
				i[1].save()
		configfile.save()
		if self.config_files[0] != config.plugins.etools.dnsname.value:
			if config.plugins.etools.dnsname.value != 0:
				self.resolv('add')
			else:
				self.resolv('clear')
		if self.config_files[1] != config.plugins.etools.ntponoff.value or self.config_files[2] != config.plugins.etools.ntpserver.value:
			if config.plugins.etools.ntponoff.value != "0":
				if not os.path.islink('/etc/network/if-up.d/ntpdate-sync'):
					enigma.eConsoleAppContainer().execute('ln -s /usr/bin/ntpdate-sync /etc/network/if-up.d/ntpdate-sync')
				remove_line(self.path, 'ntpdate')
				self.cron_ntp()
			else:
				if os.path.islink('/etc/network/if-up.d/ntpdate-sync'):
					enigma.eConsoleAppContainer().execute('unlink /etc/network/if-up.d/ntpdate-sync')
				remove_line(self.path, 'ntpdate')	
			self.ntpserver(config.plugins.etools.ntpserver.value)
		if self.config_files[3] != config.plugins.etools.droptime.value or self.config_files[4] != config.plugins.etools.dropmode.value:
			if fileExists(self.path):
				remove_line(self.path, 'drop_caches')
			if config.plugins.etools.droptime.value != '0':
				self.cron_setup()
		if self.config_files[5] != config.plugins.etools.opkg.value:
			if fileExists(self.path):
				remove_line(self.path, 'opkg')
			if config.plugins.etools.opkg.value != 0:
				self.cron_opkgupdate()
		self.config_key = [config.plugins.etools.keyrestartenigma.value, config.plugins.etools.keyrestaremu.value, config.plugins.etools.keyreloadbq.value, config.plugins.etools.keyhdmiin.value, config.plugins.etools.keyac3dmx.value, config.plugins.etools.keyemuswitch.value]
		for i in range(len(self.mapto_key)):
			self.button_map_after.append((self.mapto_key[i],self.config_key[i]))
		if set(self.button_map) == set(self.button_map_after):
			from Components.PluginComponent import plugins
			plugins.reloadPlugins()
			self.mbox = self.session.open(MessageBox,(_("configuration is saved")), MessageBox.TYPE_INFO, timeout = 3 )
		else:
			long_color = ['_RED', '_GREEN', '_YELLOW', '_BLUE']
			keyfile = open(resolveFilename(SCOPE_PLUGINS, "Extensions/etools/keymap.xml"), "w")
			keyfile.write('<keymap>\n\t<map context="GlobalActions">\n')
			for j in range(len(self.config_key)):
				if self.config_key[j] != "0":
					flag = 'm'
					for i in range(len(long_color)):
						if self.config_key[j].endswith(long_color[i]):
							flag = 'l'
					keyfile.write('\t\t<key id="%s" mapto="%s" flags="%s" />\n' % (self.config_key[j], self.mapto_key[j], flag))
			keyfile.write('\t</map>\n</keymap>\n')
			keyfile.close()
			config.plugins.etools.needrestarte2.value = False
			config.plugins.etools.needrestarte2.save()
			enigma.eConsoleAppContainer().execute('wget -q -O - http://root@127.0.0.1/web/powerstate?newstate=3')
		if config.plugins.etools.needrestarte2.value:
			config.plugins.etools.needrestarte2.value = False
			config.plugins.etools.needrestarte2.save()
			enigma.eConsoleAppContainer().execute('wget -q -O - http://root@127.0.0.1/web/powerstate?newstate=3')
######################################################################################
SKIN_ABOUT = """
<screen name="Aboutsystem" position="397,220" size="1125,750" title="">
	<ePixmap position="20,735" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,690" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget name="text" position="25,10" size="1080,675" font="Regular; 29" halign="center" noWrap="1" scrollbarMode="showOnDemand" />
</screen>"""
######################################################################################
class Aboutsystem(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skin = SKIN_ABOUT
		self.setTitle(_("E-Tools System info"))
		self.session = session
		self.emptyline = '\n'
		self.path = status_path()
		self["key_red"] = StaticText(_("Close"))
		self["text"] = ScrollLabel("")
		self.aboutsys()
	
	def cancel(self):
		self.close()
		
	def aboutsys(self):
		info = ''
		info += _("%s\n" % self.HardWareType())
		info += _("%s\n" % self.getCPUInfoString())
		if config.plugins.etools.systeminfomode.value == 'Full':
			info += self.FlashMem()
			info += self.memInfo()
		info += _("Detected storage device(s):\n%s" % self.getDisksInfo())
		info += _("Detected NIM(s):\n%s" % self.getListNims())
		info += _("Detected Network adapter(s):\n%s\n" % self.getNetworkInfo())
		if config.plugins.etools.systeminfomode.value == 'Full':
			info += self.getHdmiCecStatus()
			info += self.emptyline
		info += '\nImage: %s %s' % (self.getImageTypeString(), self.getImageVersionString())
		info += '\nKernel version: %s' % self.getKernelVersionString()
		info += self.getDVBdriverVer()
		info += self.emptyline
		if config.plugins.etools.systeminfomode.value == 'Full':
			info += self.getHostname()
			info += self.getTimezone()
			info += self.getSSLVersion()
			info += self.emptyline
			info += self.getGStreamerVersion()
			info += self.getServiceAppVersion()
			info += self.getServiceMp3Version()
			info += self.getffmpegVersion()
			info += self.getPythonVersion()
			info += self.emptyline
			info += self.getE2RestartsCont()
			info += self.getBoxUptime()
		info += self.GetEnigmaDebugLvl()
		info += self.getSkinName()
		info += self.emptyline		
		info += self.getEtoolsVersion()
		self["text"].setText(info)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "ShortcutActions", "WizardActions"], 
		{ 
		"ok": self.close,
		"red": self.close,
		"cancel": self.close,
		"up": self["text"].pageUp,
		"left": self["text"].pageUp,
		"down": self["text"].pageDown,
		"right": self["text"].pageDown,
		}, -1)
		
		
	def getTimezone(self):
		try:
			return _("\nTimeZone: %s" % open('/etc/timezone').read().replace('/', ', ').rstrip('\n'))
		except:
			return ''
			
	def getHostname(self):
		try:
			return _("\nHostname: %s" % open('/proc/sys/kernel/hostname').read().rstrip('\n'))
		except:
			return ''
		
	def getBoxUptime(self):
		try:
			time = ''
			f = open("/proc/uptime", "rb")
			secs = int(f.readline().split('.')[0])
			f.close()
			if secs > 86400:
				days = secs / 86400
				secs = secs % 86400
				time = ngettext(_("%d day"), _("%d days"), days) % days + " "
			h = secs / 3600
			m = (secs % 3600) / 60
			time += ngettext(_("%d hour"), _("%d hours"), h) % h + " "
			time += ngettext(_("%d minute"), _("%d minutes"), m) % m
			return "\nUptime: %s" % time
		except:
			return ''
			
	def getE2RestartsCont(self):
		return _("\nEnigma (re)starts: %s" % config.misc.startCounter.value)
		
	def getEtoolsVersion(self):
		try:
			from glob import glob
			etools = [x.split("Version: ") for x in open(glob("%s/info/enigma2-plugin-extensions-etools.control" % self.path[:-7])[0], "r") if x.startswith("Version:")][0]
			return _("\nE-Tools %s %s 2boom" % (etools[1].split()[-1].rstrip('\n'), chr(169)))
		except:
			return  ''
			
	def getSSLVersion(self):
		try:
			from glob import glob
			ssl = [x.split("Version: ") for x in open(glob("%s/info/openssl.control" % self.path[:-7])[0], "r") if x.startswith("Version:")][0]
			return _("\nOpenSSL version: %s" % ssl[1].split()[-1].split("-")[0].rstrip('\n'))
		except:
			return  ''
	
	def getDVBdriverVer(self):
		info = ''
		try:
			from glob import glob
			try:
				driver = [x.split("-")[-2:-1][0][-8:] for x in open(glob("%s/info/*-dvb-modules-*.control" % self.path[:-7])[0], "r") if x.startswith("Version:")][0]
				info = "%s-%s-%s" % (driver[:4], driver[4:6], driver[6:])
			except:
				try:
					driver = [x.split("Version:") for x in open(glob("%s/info/*-dvb-proxy-*.control" % self.path[:-7])[0], "r") if x.startswith("Version:")][0]
					info = "%s" % driver[1].replace("\n", "")
				except:
					driver = [x.split("Version:") for x in open(glob("%s/info/*-platform-util-*.control" % self.path[:-7])[0], "r") if x.startswith("Version:")][0]
					info = "%s" % driver[1].replace("\n", "")
		except:
			info = _("unknown")
		return _("\nDVB driver version: %s" % info)
	
	def getPythonVersion(self):		
		from sys import version as pyversion
		try:
			return _("\nPython version: %s" %  pyversion.split(' ')[0])
		except:
			return _("\nPython version: unknown")
			
	def GetEnigmaDebugLvl(self):
		try:
			return _("\nEnigma debug level: %d") % eGetEnigmaDebugLvl()
		except:
			return ''

	def getSkinName(self):
		return _('\nSkin & Resolution: %s (%sx%s)') % (config.skin.primary_skin.value.split('/')[0], getDesktop(0).size().width(), getDesktop(0).size().height())
		
	def getGStreamerVersion(self):
		info = ''
		try:
			from glob import glob
			gst = [x.split("Version: ") for x in open(glob("%s/info/gstreamer[0-9].[0-9].control" % self.path[:-7])[0], "r") if x.startswith("Version:")][0]
			info = "%s" % gst[1].split("+")[0].replace("\n", "")
		except:
			return ''
		return  _("\nMedia player: GStreamer, version %s" % info.replace("GStreamer", ""))

			
	def getffmpegVersion(self):
		try:
			from glob import glob
			ffmpeg = [x.split("Version: ") for x in open(glob("%s/info/ffmpeg.control" % self.path[:-7])[0], "r") if x.startswith("Version:")][0]
			return _("\nMedia player: ffmpeg, version %s" % ffmpeg[1].split("-")[0].replace("\n", ""))
		except:
			return  ''
			
	def getServiceAppVersion(self):
		try:
			from glob import glob
			serapp = [x.split("Version: ") for x in open(glob("%s/info/enigma2-plugin-systemplugins-serviceapp.control" % self.path[:-7])[0], "r") if x.startswith("Version:")][0]
			return _("\nMedia player: ServiceApp, version %s" % serapp[1].replace("\n", ""))
		except:
			return  ''
	
	def getServiceMp3Version(self):
		try:
			from glob import glob
			sermp3 = [x.split("Version: ") for x in open(glob("%s/info/enigma2-plugin-systemplugins-servicemp3.control" % self.path[:-7])[0], "r") if x.startswith("Version:")][0]
			return _("\nMedia player: ServiceMp3, version %s" % sermp3[1].replace("\n", ""))
		except:
			return ''

	def getImageTypeString(self):
		try:
			if os.path.isfile("/etc/issue"):
				for line in open("/etc/issue"):
					if not line.startswith(('Welcome', '\n')):
						return(line.capitalize()[:-6].strip())
		except:
			pass
		return _("undefined")
		
	def getKernelVersionString(self):
		try:
			return open("/proc/version").read().strip('\n').split()[2]
		except:
			return _("unknown")
			
	def getImageVersionString(self):
		try:
			st = os.stat(self.path)
			tm = time.localtime(st.st_mtime)
			if tm.tm_year >= 2011:
				return time.strftime("%d.%m.%Y", tm)
		except:
			pass
		return _("unavailable")
		
	def memInfo(self):
		for line in open("/proc/meminfo"):
			if line.startswith("MemTotal:"):
				memtotal = line.split()[1]
			elif line.startswith("MemFree:"):
				memfree = line.split()[1]
		return _("Memory: %0.3f GB  (%0.3f GB free)\n") % (int(memtotal)/float(1024**2), int(memfree)/float(1024**2))
		

	def FlashMem(self):
		size = avail = 0
		st = os.statvfs("/")
		avail = st.f_bsize * st.f_bavail/float(1024**3)
		size = st.f_bsize * st.f_blocks/float(1024**3)
		return _("Flash: %0.3f GB  (%0.3f GB free)\n") % (size , avail)
	
	def getNetworkInfo(self):
		info = ''
		currentdev = 'none'
		nonconectdev = ''
		devname = []
		ipaddr = []
		devtype = ['et', 'wl', 'ra', 'pp']
		if fileExists('/proc/net/dev'):
			for line in open('/proc/net/dev'):
				for i in range(len(devtype)):
					if line.strip().startswith(devtype[i]):
						devname.append(line.split(':')[0].strip())
			if fileExists('/proc/net/fib_trie'):
				for line in open('/proc/net/fib_trie'):
					if line.strip().startswith('|--') and not line.strip().endswith(('.255', '.0', '.1')):
							ipaddr.append(line.replace('|--', '').strip())
			for i in range(len(devname)):
				if fileExists('/sys/class/net/%s/operstate' % devname[i]):
					if 'up' in open('/sys/class/net/%s/operstate' % devname[i]).read():
						currentdev = devname[i]
			if currentdev != '':
				info += '(%s) IP: %s  ' % (currentdev, ipaddr[0])
			for i in range(len(devname)):
				if fileExists('/sys/class/net/%s/address' % devname[i]):
					if devname[i] == currentdev:
						info += 'MAC: %s' % open('/sys/class/net/%s/address' % devname[i]).read().strip('\n')
					else:
						nonconectdev += _('\nNot Connected (%s) MAC: %s' % (devname[i], open('/sys/class/net/%s/address' % devname[i]).read().strip('\n')))
			if nonconectdev != '':
				info += nonconectdev
		return info
		
	def getHdmiCecStatus(self):
		try:
			if config.hdmicec.enabled.value:
				if config.hdmicec.fixed_physical_address.value != "0.0.0.0":
					address = config.hdmicec.fixed_physical_address.value
				else:
					address = _("not set")
				return  _("HDMI-CEC address: %s" % address)
			else:
				return _("HDMI-CEC: not enabled")
		except:
			return _("HDMI-CEC: not enabled")
			
	def getListNims(self):
		info = ''
		nims = nimmanager.nimListCompressed()
		for count in range(len(nims)):
			if count < 4:
				self["Tuner" + str(count)] = StaticText(nims[count])
			else:
				self["Tuner" + str(count)] = StaticText("")
			info += nims[count] + "\n"
		return info
		
	def HardWareType(self):
		if os.path.isfile("/proc/stb/info/boxtype"):
			return open("/proc/stb/info/boxtype").read().strip().capitalize() 
		if os.path.isfile("/proc/stb/info/vumodel"):
			return "VU+ " + open("/proc/stb/info/vumodel").read().strip().capitalize()
		if os.path.isfile("/proc/stb/info/model"):
			return open("/proc/stb/info/model").read().strip().capitalize()
		return _("unavailable")
		
	def getCPUInfoString(self):
		try:
			cpu_count = 0
			cpu_speed = 0
			processor = ""
			for line in open("/proc/cpuinfo").readlines():
				line = [x.strip() for x in line.strip().split(":")]
				if not processor and line[0] in ("system type", "model name", "Processor"):
					processor = line[1].split()[0]
				elif not cpu_speed and line[0] == "cpu MHz":
					cpu_speed = "%1.0f" % float(line[1])
				elif line[0] == "processor":
					cpu_count += 1

			if processor.startswith("ARM") and os.path.isfile("/proc/stb/info/chipset"):
				processor = "%s (%s)" % (open("/proc/stb/info/chipset").readline().strip().upper(), processor)

			if not cpu_speed:
				try:
					cpu_speed = int(open("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq").read()) / 1000
				except:
					try:
						import binascii
						cpu_speed = int(int(binascii.hexlify(open('/sys/firmware/devicetree/base/cpus/cpu@0/clock-frequency', 'rb').read()), 16) / 100000000) * 100
					except:
						cpu_speed = "-"

			temperature = None
			freq = _("MHz")
			if os.path.isfile('/proc/stb/fp/temp_sensor_avs'):
				temperature = open("/proc/stb/fp/temp_sensor_avs").readline().replace('\n', '')
			elif os.path.isfile('/proc/stb/power/avs'):
				temperature = open("/proc/stb/power/avs").readline().replace('\n', '')
			elif os.path.isfile('/proc/stb/fp/temp_sensor'):
				temperature = open("/proc/stb/fp/temp_sensor").readline().replace('\n', '')
			elif os.path.isfile("/sys/devices/virtual/thermal/thermal_zone0/temp"):
				try:
					temperature = int(open("/sys/devices/virtual/thermal/thermal_zone0/temp").read().strip()) / 1000
				except:
					pass
			elif os.path.isfile("/proc/hisi/msp/pm_cpu"):
				try:
					temperature = re.search('temperature = (\d+) degree', open("/proc/hisi/msp/pm_cpu").read()).group(1)
				except:
					pass
			if temperature:
				return "%s %s %s (%s) %s\xb0C" % (processor, cpu_speed, freq, ngettext("%d core", "%d cores", cpu_count) % cpu_count, temperature)
			return "%s %s %s (%s)" % (processor, cpu_speed, freq, ngettext("%d core", "%d cores", cpu_count) % cpu_count)
		except:
			return _("undefined")

	def getDisksInfo(self):
		info = ""
		hddlist = harddiskmanager.HDDList()
		if hddlist:
			for count in range(len(hddlist)):
				hdd = hddlist[count][1]
				if int(hdd.free()) > 1024:
					info += ((_("%s  %s  (%0.2f GB free)\n") % (hdd.model(), hdd.capacity(), hdd.free()/float(1024))))
				else:
					info += ((_("%s  %sf  (%0.2f MB free)\n") % (hdd.model(), hdd.capacity(),hdd.free())))
		else:
			info = _("none\n")
		return info

######################################################################################
class EHotKey():
	def __init__(self):
		self.dialog = None

	def gotSession(self, session):
		self.session = session
		self.mainconfig = []
		self.tmpconfig = '/tmp/emuconfig.tmp'
		self.timeout = 2
		self.mapto_key = ['renigma2', 'restemu', 'relbq', 'hdmiin', 'ac3mix', 'eswitch']
		self.config_key = [config.plugins.etools.keyrestartenigma.value, config.plugins.etools.keyrestaremu.value, config.plugins.etools.keyreloadbq.value, config.plugins.etools.keyhdmiin.value, config.plugins.etools.keyac3dmx.value, config.plugins.etools.keyemuswitch.value]
		long_color = ['_RED', '_GREEN', '_YELLOW', '_BLUE']
		keymap = resolveFilename(SCOPE_PLUGINS, "Extensions/etools/keymap.xml")
		if not fileExists(keymap):
			keyfile = open(keymap, "w")
			keyfile.write('<keymap>\n\t<map context="GlobalActions">\n')
			for j in range(len(self.config_key)):
				if self.config_key[j] != "0":
					flag = 'm'
					for i in range(len(long_color)):
						if self.config_key[j].endswith(long_color[i]):
							flag = 'l'
					keyfile.write('\t\t<key id="%s" mapto="%s" flags="%s" />\n' % (self.config_key[j], self.mapto_key[j], flag))
			keyfile.write('\t</map>\n</keymap>\n')
			keyfile.close()
		if config.plugins.etools.restartmute.value:
			if config.plugins.etools.restartcount.value != config.misc.startCounter.value:
				config.plugins.etools.restartcount.save()
				self.muteOn()
		
		if config.plugins.etools.restartcount.value != config.misc.startCounter.value:
			if config.plugins.etools.dnsname.value != 0:
				self.resolv('add')
			else:
				self.resolv('clear')

		if fileExists(keymap):	
			global globalActionMap
			readKeymap(keymap)
			if config.plugins.etools.keyac3dmx.value != "0":
				globalActionMap.actions['ac3mix'] = self.downmix
			if config.plugins.etools.keyreloadbq.value != "0":
				globalActionMap.actions['relbq'] = self.bouqreload
			if config.plugins.etools.keyrestaremu.value != "0":
				globalActionMap.actions['restemu'] = self.emurestart
			if config.plugins.etools.keyhdmiin.value != "0": 
				globalActionMap.actions['hdmiin'] = self.switchhdmiin
			if config.plugins.etools.keyrestartenigma.value != "0":
				globalActionMap.actions['renigma2'] = self.enigmarestart
			if config.plugins.etools.keyemuswitch.value != '0':
				globalActionMap.actions['eswitch'] = self.emuswitch
	
	def bouqreload(self):
		self.session.open(BouquetsReload)

	def emuswitch(self):
		self.session.open(qemuswitchconfig)
		
	def emurestart(self):
		self.session.open(qemurestart)
		
	def muteOn(self):
		eDVBVolumecontrol.getInstance().volumeMute()
		
	def enigmarestart(self):
		enigma.eConsoleAppContainer().execute('wget -q -O - http://root@127.0.0.1/web/powerstate?newstate=3')

	def downmix(self):
		if config.av.downmix_ac3.value == False or config.av.downmix_ac3.value == True:
			if config.av.downmix_ac3.value == False:
				config.av.downmix_ac3.value = True
				config.plugins.etools.ac3state.value = _("Off")
				self.message(_("Downmix AC3,DTS is ON"))
			else:
				config.av.downmix_ac3.value = False
				config.plugins.etools.ac3state.value = _("On")
				self.message(_("Downmix AC3,DTS is OFF"))
			config.av.downmix_ac3.save()
		else:
			if config.av.downmix_ac3.value == "passthrough":
				config.av.downmix_ac3.value = "downmix"
				config.av.downmix_dts.value = "downmix"
				config.plugins.etools.ac3state.value = _("Off")
				self.message(_("Downmix AC3,DTS is ON"))
			else:
				config.av.downmix_ac3.value = "passthrough"
				config.av.downmix_dts.value = "passthrough"
				config.plugins.etools.ac3state.value = _("On")
				self.message(_("Downmix AC3,DTS is OFF"))
			config.av.downmix_ac3.save()
			config.av.downmix_dts.save()
		config.plugins.etools.ac3state.save()
		
	def switchhdmiin(self):
		self.lasttvsevice = config.tv.lastservice.value
		self.reftozap = '8192:0:1:0:0:0:0:0:0:0:'
		try:
			csref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if csref is not None:
				if not csref.toString().startswith("4097:0:0:0:0:0:0:0:0:0:/"):
					if not csref.toString().startswith("8192"):
						self.session.nav.playService(eServiceReference(self.reftozap))
						config.plugins.etools.hdmiinonoff.value = _("Off")
					else:
						self.session.nav.playService(eServiceReference(self.lasttvsevice))
						config.plugins.etools.hdmiinonoff.value = _("On")
					config.plugins.etools.hdmiinonoff.save()
		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))
			config.plugins.etools.needrestarte2.value = True
			config.plugins.etools.needrestarte2.save()
			self.message(_("Need restart Enigma2"))
				
	def resolv(self, do):
		DNSIP = []
		for i in range(1, len(DNSLIST)):
			DNSIP.append(DNSLIST[i][-2])
			DNSIP.append(DNSLIST[i][-1])
		if fileExists('/etc/resolv.conf'):
			for i in range(len(DNSIP)):
				remove_line('/etc/resolv.conf', DNSIP[i])
			if do == 'add':
				add_line('/etc/resolv.conf', 'nameserver %s\n' % DNSLIST[config.plugins.etools.dnsname.value][-2])
				add_line('/etc/resolv.conf', 'nameserver %s\n' % DNSLIST[config.plugins.etools.dnsname.value][-1])

	def message(self, what):
		try:
			self.mbox = self.session.open(MessageBox,(what), MessageBox.TYPE_INFO, timeout = self.timeout)
		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))	
#########################################################################################################
SKIN_INST = """
<screen name="einstaller" position="center,220" size="1125,610" title="">
	<widget source="menu" render="Listbox" position="26,10" size="1080,525" scrollbarMode="showOnDemand">
		<convert type="TemplatedMultiContent">
			{"template": [
				MultiContentEntryText(pos = (105, 3), size = (975, 38), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
				MultiContentEntryText(pos = (120, 43), size = (945, 24), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
				MultiContentEntryPixmapAlphaTest(pos = (7, 7), size = (75, 60), png = 2), # index 4 is the pixmap
				],
			"fonts": [gFont("Regular", 32),gFont("Regular", 23)],
			"itemHeight": 75
			}
		</convert>
	</widget>
	<ePixmap position="20,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/green.png" transparent="1" alphatest="on" />
	<ePixmap position="526,590" zPosition="1" size="280,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/yellow.png" transparent="1" alphatest="on" />
	<ePixmap position="809,590" zPosition="1" size="280,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/blue.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_green" render="Label" position="273,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_yellow" render="Label" position="526,545" zPosition="2" size="280,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_blue" render="Label" position="809,545" zPosition="2" size="280,45" valign="center" halign="center" font="Regular;30" transparent="1" />
</screen>"""
######################################################################################
class einstaller(Screen):
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.skin = SKIN_INST
		if config.plugins.etools.multifilemode.value == 'Multi':
			self.setTitle(_("E-Intaller MultiSelect Mode (press [info] for --force change)"))
		else:
			self.setTitle(_("E-Intaller SingleSelect Mode (press [info] for --force change)"))	
		self.session = session
		self.forcemode = config.plugins.etools.force.value
		self.forcecommand = FORCECOMMAND
		self.current_index = self.forcecommand.index(self.forcemode)
		self.workdir = []
		self.list = []
		self.commamd_line_ipk = []
		self.commamd_line_tar = []
		self.force_install = False
		self.status = False
		self.pngfile = ""
		self.ipk_off = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/ipk_off.png"))
		self.tar_off = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/tar_off.png"))
		self.ipk_on = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/ipk_on.png"))
		self.tar_on = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/tar_on.png"))
		self["menu"] = List(self.list)
		self.listofpacket()
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "EPGSelectActions", "SetupActions"],
			{
				"cancel": self.cancel,
				"ok": self.press_ok,
				"green": self.all_install,
				"red": self.cancel,
				"yellow": self.install_force,
				"blue": self.restart_enigma,
				"info": self.infoKey,
			},-1)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Install"))
		self["key_yellow"] = StaticText(_("%s")% self.forcemode.replace('--force', ''))
		self["key_blue"] = StaticText(_("Restart"))
		
	def mount_point(self):
		searchPaths = []
		if fileExists('/proc/mounts'):
			for line in open('/proc/mounts'):
				if "/dev/sd" in line:
					searchPaths.append(line.split()[1].replace('\\040', ' ') + config.plugins.etools.userdir.value)
		searchPaths.append('/tmp/')
		return searchPaths
		
	def press_ok(self):
		if config.plugins.etools.multifilemode.value == 'Multi':
			self.mark_list()
		else:
			self.all_install()
			
	def install_force(self):
		self.force_install = True
		self.all_install()
			
	def mark_list(self):
		line_old = self["menu"].getCurrent()
		if line_old is not None:
			if not line_old[-2]:
				if ".ipk" in line_old[0]:
					self.pngfile = self.ipk_on
					self.commamd_line_ipk.append(line_old[-1])
				else:
					self.pngfile = self.tar_on
					self.commamd_line_tar.append('tar -C/ -xzpvf %s' % line_old[-1])
				self.status = True
			else:
				if ".ipk" in line_old[0]:
					self.pngfile = self.ipk_off
					self.commamd_line_ipk.remove(line_old[-1])
				else:
					self.pngfile = self.tar_off
					self.commamd_line_tar.remove('tar -C/ -xzpvf %s' % line_old[-1])
				self.status = False
			line_new = (line_old[0], line_old[1], self.pngfile, self.status, line_old[-1])	
			self["menu"].modifyEntry(self["menu"].getIndex(), line_new)
			if self["menu"].getIndex() + 1 >= self["menu"].count():
				self["menu"].setIndex(0)
			else:
				self["menu"].selectNext()
				
	def infoKey(self):
		self.current_index = self.current_index + 1
		if self.current_index == len(self.forcecommand):
			self.current_index = 0
		self.forcemode = self.forcecommand[self.current_index]
		config.plugins.etools.force.value = self.forcemode
		config.plugins.etools.force.save()
		self["key_yellow"].setText(_("%s")% self.forcemode.replace('--force', ''))

	def all_install(self):
		line_old = self["menu"].getCurrent()
		if line_old is not None:
			if config.plugins.etools.multifilemode.value != 'Multi':
				self.commamd_line_tar = []
				self.commamd_line_ipk = []
				if '.ipk' in self["menu"].getCurrent()[-1]:
					self.commamd_line_ipk.append(self["menu"].getCurrent()[-1])
				else:
					self.commamd_line_tar.append('tar -C/ -xzpvf %s' % self["menu"].getCurrent()[-1])
			force_string = ''
			if self.force_install:
				force_string = " %s " % self.forcemode
			if len(self.commamd_line_ipk) >= 1 and len(self.commamd_line_tar) >= 1:
				self.session.open(Console, title = _("Install packets"), cmdlist = ["opkg install %s %s && %s" % (force_string, ' '.join(self.commamd_line_ipk), ' && '.join(self.commamd_line_tar))])
			elif len(self.commamd_line_ipk) >= 1:
				self.session.open(Console, title = _("Install packets"), cmdlist = ["opkg install %s %s" % (force_string, ' '.join(self.commamd_line_ipk))])
			elif len(self.commamd_line_tar) >= 1:
				self.session.open(Console,title = _("Install tar.gz, bh.tgz, nab.tgz"), cmdlist = ["%s" % ' && '.join(self.commamd_line_tar)])
			self.force_install = False
		
	def listofpacket(self):
		self.workdir = self.mount_point()
		for i in range(len(self.workdir)):
			if pathExists(self.workdir[i]):
				ipklist = os.listdir(self.workdir[i])
				for filename in ipklist:
					if filename.endswith('tar.gz') or filename.endswith('bh.tgz') or filename.endswith('nab.tgz'):
						try:
							self.list.append((filename.strip("\n"), "%s, %d Kb,  %s" % (self.workdir[i], (os.path.getsize(self.workdir[i] + filename.strip("\n")) / 1024),time.ctime(os.path.getctime(self.workdir[i] + filename.strip("\n")))), self.tar_off, self.status, self.workdir[i] + filename.strip("\n")))
						except:
							pass
					elif filename.endswith('.ipk'):
						try:
							self.list.append((filename.strip("\n"), "%s, %d Kb,  %s" % (self.workdir[i],(os.path.getsize(self.workdir[i] + filename.strip("\n")) / 1024),time.ctime(os.path.getctime(self.workdir[i] + filename.strip("\n")))), self.ipk_off, self.status, self.workdir[i] + filename.strip("\n")))
						except:
							pass
		self.list.sort()
		self["menu"].setList(self.list)
		
	def restart_enigma(self):
		self.session.open(TryQuitMainloop, 3)
	
	def cancel(self):
		self.close()
######################################################################################
SKIN_EMU = """
<screen name="emuSelelection" position="center,220" size="1125,610" title="">
	<widget source="menu" render="Listbox" position="20,10" size="1080,225" scrollbarMode="showOnDemand">
		<convert type="TemplatedMultiContent">
			{"template": [
				MultiContentEntryText(pos = (105, 3), size = (975, 38), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
				MultiContentEntryText(pos = (120, 43), size = (945, 24), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
				MultiContentEntryPixmapAlphaTest(pos = (7, 7), size = (75, 60), png = 2), # index 4 is the pixmap
				],
			"fonts": [gFont("Regular", 32),gFont("Regular", 23)],
			"itemHeight": 75
			}
		</convert>
	</widget>
	<ePixmap position="20,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/green.png" transparent="1" alphatest="on" />
	<ePixmap position="526,590" zPosition="1" size="280,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/yellow.png" transparent="1" alphatest="on" />
	<ePixmap position="809,590" zPosition="1" size="280,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/blue.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_green" render="Label" position="273,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_yellow" render="Label" position="526,545" zPosition="2" size="280,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_blue" render="Label" position="809,545" zPosition="2" size="280,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget name="text" position="20,335" size="1080,200" font="Regular; 29" halign="center" noWrap="1" />
<widget source="inmemory" render="Label" position="20,270" size="1080,40" font="Regular; 30" halign="center" noWrap="1" />
</screen>"""
######################################################################################
class emuSelelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skin = SKIN_EMU
		self.setTitle(_("E-Softcam Manager"))
		self.session = session
		self.iConsole = iConsole()
		self.current_emu = ''
		self.emutype = ''
		self.list = []
		self.indexpos = None
		self["menu"] = List(self.list)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
			{
				"cancel": self.cancel,
				"ok": self.ok,
				"green": self.ok,
				"red": self.cancel,
				"yellow": self.emuStopOperation,
				"blue": self.emuRestartOperation,
			},-1)
		self.list = [ ]
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Start"))
		self["key_yellow"] = StaticText(_("Stop"))
		self["key_blue"] = StaticText(_("Restart"))
		self["text"] = ScrollLabel("")
		self["inmemory"] = StaticText()
		self.update_rc()
		self.listecm()
		self.Timer = eTimer()
		self.Timer.callback.append(self.listecm)
		self.Timer.start(1000*4, False)
		self.selemulist()
		
	def camfile(self, filename, what):
		file_write = open(filename, 'w')
		file_write.write(what)
		file_write.close()

	def update_rc(self):
		file_text = '# Placeholder for no cam'	
		softcam_files =['/etc/init.d/softcam', '/etc/rc0.d/K50softcam', '/etc/rc1.d/K50softcam', '/etc/rc2.d/S50softcam', '/etc/rc3.d/S50softcam', '/etc/rc4.d/S50softcam', '/etc/rc5.d/S50softcam', '/etc/rc6.d/K50softcam',]
		cardserver_files =['/etc/init.d/cardserver', '/etc/rc0.d/K50cardserver', '/etc/rc1.d/K50cardserver', '/etc/rc2.d/S50cardserver', '/etc/rc3.d/S50cardserver', '/etc/rc4.d/S50cardserver', '/etc/rc5.d/S50cardserver', '/etc/rc6.d/K50cardserver',]
		if not fileExists('/etc/init.d/softcam.None'):
			self.camfile('/etc/init.d/softcam.None', file_text)
			os.chmod('/etc/init.d/softcam.None', 777)
		for name_files in range(len(softcam_files)):
			if not fileExists(softcam_files[name_files]):
				enigma.eConsoleAppContainer().execute('ln -s /etc/init.d/softcam %s' % softcam_files[name_files])			
		if not fileExists('/etc/init.d/cardserver.None'):
			self.camfile('/etc/init.d/cardserver.None', file_text)
			os.chmod('/etc/init.d/cardserver.None', 777)
		for name_files in range(len(cardserver_files)):
			if not fileExists(cardserver_files[name_files]):
				enigma.eConsoleAppContainer().execute('ln -s /etc/init.d/cardserver %s' % cardserver_files[name_files])

	def selemulist(self):
		self.list = []
		typeemu = ' '
		camdlist = os.listdir("/etc/init.d/")
		for line in camdlist:
			if '.None' not in line and '.none' not in line:
				if line.split(".")[0] == 'softcam':
					typeemu = 'softcam'
					if self.emuversion(line) == self.emuversion('softcam'):
						softpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/%s" % 'emu_on.png'))
					else:
						softpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/%s" % 'emu_off.png'))
				elif line.split(".")[0] == 'cardserver':
					typeemu = 'cardserver'
					if self.emuversion(line) == self.emuversion('cardserver'):
						softpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/%s" % 'card_on.png'))
					else:
						softpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/%s" % 'card_off.png'))
				try:
					if 'softcam.' in line or 'cardserver.' in line:
						self.list.append((line, self.emuversion(line), softpng, typeemu))
				except:
					pass
		self.list.sort()
		self["menu"].setList(self.list)
		self.setTitle(_("E-Softcam Manager"))
		if self.indexpos is not None:
			self["menu"].setIndex(self.indexpos)
		self.name_in_memory()
	
	def emuversion(self, what):
		emuname = ' '
		nameemu = []
		if fileExists('/etc/init.d/%s' % what.split("\n")[0]):
			try:
				for line in open('/etc/init.d/%s' % what.split("\n")[0]):
					if 'echo' in line:
						nameemu.append(line)
				emuname =  '%s' % nameemu[1].split('"')[1]
			except:
				emuname = ' '
		return emuname
		
	def cut_name(self, what):
		count = 0
		what = what.replace('_', ' ').replace('-', ' ')
		count = len(what.split())
		if count <= 1:
			return what
		else:
			return what.split()[0]

	def name_in_memory(self):
		self.iConsole.ePopen("ps", self.stdout_find)

	def stdout_find(self, result, retval, extra_args):
		status = ''
		name_emu = self.cut_name(self.emuversion('softcam'))
		name_card = self.cut_name(self.emuversion('cardserver'))
		if name_card != ' ':
			for line in result.splitlines(True):
				if name_card.split()[0].upper() in result.upper():
					status += '%s ' % name_card
					break
		if name_emu != ' ':
			for line in result.splitlines(True):
				if name_emu.split()[0].upper() in result.upper():
					status += '%s' % name_emu
					break
		try:
			if status != '':
				self["inmemory"].text = _("%s loaded in memory") % status
			else:
				self["inmemory"].text = _("not loaded modules")
		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))

	def listecm(self):
		self["text"].setText(ecm_view())
##################################################################################
	def ok(self):
		try:
			self.emutype = self["menu"].getCurrent()[3]
			self.current_item = self["menu"].getCurrent()[0]
			if self["menu"].getCurrent()[1] != self.emuversion(self.emutype):
				self.setTitle(_("Please wait"))
				self.indexpos = self["menu"].getIndex()
				self.session.openWithCallback(self.selemulist, start_cam, self.emutype, self.current_item)
		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))
##################################################################################
	def emuStopOperation(self):
		try:
			self.setTitle(_("Please wait"))
			self.emutype = self["menu"].getCurrent()[3]
			self.current_item = self["menu"].getCurrent()[0]
			if self.emuversion(self.emutype) != ' ':
				self.indexpos = self["menu"].getIndex()
				self.session.openWithCallback(self.selemulist, stop_cam, self.emutype)
			config.plugins.etools.activeemu.value = _("None")
			config.plugins.etools.activeemu.save()
		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))
##################################################################################
	def emuRestartOperation(self):
		try:
			self.setTitle(_("Please wait"))
			self.emutype = self["menu"].getCurrent()[3]
			if self.emuversion(self.emutype) != ' ':
				self.indexpos = self["menu"].getIndex()
				self.session.openWithCallback(self.selemulist, restart_cam, self.emutype)
		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))

	def cancel(self):
		self.close()
##################################################################################
SKIN_DWN = """
<screen name="satusmessage" position="center,220" size="940,55" title="Please wait">
  <widget source="status" render="Label" position="25,7" size="900,40" zPosition="2" font="Regular;30" halign="center" transparent="1" />
</screen>"""
##################################################################################
class start_cam(Screen):
	def __init__(self, session, emutype, current_item):
		Screen.__init__(self, session)
		self.session = session
		self.skin = SKIN_DWN
		self.emutype = emutype
		self.current_item = current_item
		self.setTitle(_("Please wait"))
		self["status"] = StaticText()
		self.iConsole = iConsole()
		self["status"].text = _("Stoping...")
		self.iConsole.ePopen("/etc/init.d/%s stop" % self.emutype, self.emuRemoveStartScript)
	def emuRemoveStartScript(self, result, retval, extra_args):
		self["status"].text = _("Removing startscript...")
		self.iConsole.ePopen("rm -f /etc/init.d/%s" % self.emutype, self.emuRemoveEcmInfo)

	def emuRemoveEcmInfo(self, result, retval, extra_args):
		self["status"].text = _("Removing ecm.info...")
		self.iConsole.ePopen("rm -f /tmp/ecm.info", self.emuAddStartScript)

	def emuAddStartScript(self, result, retval, extra_args):
		self["status"].text = _("Adding startscript...")
		self.iConsole.ePopen("ln -s /etc/init.d/%s /etc/init.d/%s" % (self.current_item, self.emutype),  self.emuChmodStartScript)

	def emuChmodStartScript(self, result, retval, extra_args):
		self.iConsole.ePopen("chmod 777 /etc/init.d/%s" %  self.emutype, self.emuScriptStart)

	def emuScriptStart(self, result, retval, extra_args):
		self["status"].text = _("Starting...")
		self.iConsole.ePopen("/etc/init.d/%s start" % self.emutype, self.sleep_time)
	
	def sleep_time(self, result, retval, extra_args):
		self.iConsole.ePopen("sleep 3", self.emuStartEndOperation)

	def emuStartEndOperation(self, result, retval, extra_args):
		config.plugins.etools.activeemu.value = self.emuversion(self.emutype)
		config.plugins.etools.activeemu.save()
		self["status"].setText(' ')
		from Components.PluginComponent import plugins
		plugins.reloadPlugins()
		self.close()

	def emuversion(self, what):
		emuname = ' '
		nameemu = []
		if fileExists('/etc/init.d/%s' % what.split("\n")[0]):
			try:
				for line in open('/etc/init.d/%s' % what.split("\n")[0]):
					if 'echo' in line:
						nameemu.append(line)
				emuname =  '%s' % nameemu[1].split('"')[1]
			except:
				emuname = ' '
		return emuname
####################################################################################################
class restart_cam(Screen):
	def __init__(self, session, emutype):
		Screen.__init__(self, session)
		self.session = session
		self.skin = SKIN_DWN
		self.emutype = emutype
		self.setTitle(_("Please wait"))
		self["status"] = StaticText()
		self.iConsole = iConsole()
		self["status"].text = _("Restarting...")
		self.iConsole.ePopen("/etc/init.d/%s restart" % self.emutype, self.sleep_time)
		
	def sleep_time(self, result, retval, extra_args):
		self.iConsole.ePopen("sleep 3", self.emuRestartOperationEnd)
		
	def emuRestartOperationEnd(self, result, retval, extra_args):
		self["status"].setText(' ')
		self.close()
####################################################################################################
class stop_cam(Screen):
	def __init__(self, session, emutype):
		Screen.__init__(self, session)
		self.session = session
		self.skin = SKIN_DWN
		self.emutype = emutype
		self.setTitle(_("Please wait"))
		self["status"] = StaticText()
		self.iConsole = iConsole()
		self["status"].text = _("Stoping...")
		self.iConsole.ePopen("/etc/init.d/%s stop" % self.emutype, self.emuRemoveScriptStop)
			
	def emuRemoveScriptStop(self, result, retval, extra_args):
		self["status"].text = _("Removing startscript...")
		self.iConsole.ePopen("rm -f /etc/init.d/%s" % self.emutype, self.emuRemoveEcmInfoStop)
			
	def emuRemoveEcmInfoStop(self, result, retval, extra_args):
		self["status"].text = _("Removing ecm.info...")
		self.iConsole.ePopen("rm -f /tmp/ecm.info", self.emuCreateNone)
			
	def emuCreateNone(self, result, retval, extra_args):
		self["status"].text = _("Creating None script...")
		if fileExists("/etc/init.d/%s.None" % self.emutype):
			self.iConsole.ePopen("ln -s /etc/init.d/%s.None /etc/init.d/%s" % (self.emutype, self.emutype),  self.emuChmodStopScript)
		elif fileExists("/etc/init.d/%s.none" % self.emutype):
			self.iConsole.ePopen("ln -s /etc/init.d/%s.none /etc/init.d/%s" % (self.emutype, self.emutype),  self.emuChmodStopScript)
		else:
			self.iConsole.ePopen("echo -e '# Placeholder for no cam' >> /etc/init.d/%s.None && ln -s /etc/init.d/%s.None /etc/init.d/%s" % \
				(self.emutype, self.emutype, self.emutype), self.emuChmodStopScript)
				
	def emuChmodStopScript(self, result, retval, extra_args):
		self.iConsole.ePopen("chmod 777 /etc/init.d/%s" %  self.emutype, self.sleep_time)
		
	def sleep_time(self, result, retval, extra_args):
		self.iConsole.ePopen("sleep 3", self.emuStopEndOperation)
		
	def emuStopEndOperation(self, result, retval, extra_args):
		from Components.PluginComponent import plugins
		plugins.reloadPlugins()
		self["status"].setText(' ')
		self.close()
######################################################################################
class qemurestart(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.iConsole = iConsole()
		self.skin = SKIN_DWN
		self.setTitle(_("Please wait"))
		self["status"] = StaticText()
		self.service = None
		if fileExists(resolveFilename(SCOPE_PLUGINS, "Extensions/AlternativeSoftCamManager/plugin.py")):
			self.service = self.session.nav.getCurrentlyPlayingServiceReference()
			emunam = config.plugins.AltSoftcam.actcam.value
			if emunam != "none":
				self.iConsole.ePopen("killall -15 %s" % emunam)
				if self.service:
					self.session.nav.stopService()
				self.iConsole.ePopen("%s && sleep 3" % getcamcmd(emunam), self.finish)
		if fileExists("/etc/init.d/softcam") and fileExists("/etc/init.d/cardserver"):
			if self.isCamNone('softcam') and self.isCamNone('cardserver'):
				self["status"].text = _("Softcam or/and Cardserver not active")
				self.notFoundActiveCam()
		if fileExists("/etc/init.d/softcam") or fileExists("/etc/init.d/cardserver"):
			if fileExists("/etc/init.d/softcam") and not self.isCamNone('softcam'):
				self.iConsole.ePopen("/etc/init.d/softcam restart && sleep 3", self.finish)
			if fileExists("/etc/init.d/cardserver") and not self.isCamNone('cardserver'):
				self.iConsole.ePopen("/etc/init.d/cardserver restart && sleep 3", self.finish)
			self["status"].text = _("Restarting %s") % self.emuname()

	def notFoundActiveCam(self):
		self.close()
			
	def finish(self, result, retval, extra_args):
		if self.service is not None:
			self.session.nav.playService(self.service)
		self.close()
		
	def isCamNone(self, camlink):
		if fileExists("/etc/init.d/%s" % camlink):
			if '# Placeholder for no cam' in open("/etc/init.d/%s" % camlink).read():
				return True
		return False

	def emuname(self):
		serlist = camdlist = None
		nameemu = nameser = []
		ecminfo = ''
		#Alternative SoftCam Manager 
		if os.path.isfile(resolveFilename(SCOPE_PLUGINS, "Extensions/AlternativeSoftCamManager/plugin.py")): 
			if config.plugins.AltSoftcam.actcam.value != "none": 
				return config.plugins.AltSoftcam.actcam.value 
			else: 
				return None
		#Pli
		if fileExists("/etc/init.d/softcam") or fileExists("/etc/init.d/cardserver"):
			if fileExists("/etc/init.d/softcam") and not self.isCamNone('softcam'):
				for line in open("/etc/init.d/softcam"):
					if "echo" in line:
						nameemu.append(line)
				if len(nameemu) > 1:
					camdlist = "%s" % nameemu[1].split('"')[1]
			if fileExists("/etc/init.d/cardserver") and not self.isCamNone('cardserver'):
				for line in open("/etc/init.d/cardserver"):
					if "echo" in line:
						nameser.append(line)
				if len(nameser) > 1:
					serlist = "%s" % nameser[1].split('"')[1]
			if serlist is not None and camdlist is not None:
				return ("%s %s" % (serlist, camdlist))
			elif camdlist is not None:
				return "%s" % camdlist
			elif serlist is not None:
				return "%s" % serlist
			return ""
		else:
			emu = ""
			ecminfo = "%s %s" % (cardserver.split('\n')[0], emu.split('\n')[0])
		return ecminfo
######################################################################################
class qemuswitchconfig(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.iConsole = iConsole()
		self.skin = SKIN_DWN
		CCCAM = ['/etc/CCcam.cfg']
		MGCAMD = ['/usr/keys/newcamd.list', '/usr/keys/priority.list', '/usr/keys/ignore.list', '/usr/keys/replace.list', '/usr/keys/mg_cfg']
		NCAM = ['/etc/tuxbox/config/ncam.conf', '/etc/tuxbox/config/ncam.server', '/etc/tuxbox/config/ncam.dvbapi', '/etc/tuxbox/config/ncam.user', '/etc/tuxbox/config/ncam.provid', '/etc/tuxbox/config/ncam.servid2', '/etc/tuxbox/config/ncam.fs']
		OSCAM = ['/etc/tuxbox/config/oscam.conf', '/etc/tuxbox/config/oscam.server', '/etc/tuxbox/config/oscam.dvbapi', '/etc/tuxbox/config/oscam.user', '/etc/tuxbox/config/oscam.provid', '/etc/tuxbox/config/oscam.servid2', '/etc/tuxbox/config/oscam.fs']
		WICARDD = ['/etc/tuxbox/config/wicardd.conf']
		EMU = [CCCAM, MGCAMD, NCAM, OSCAM, WICARDD]
		emuname = ['cccam', 'mgcamd', 'ncam', 'oscam', 'wicardd']
		self.mainconfig = []
		self.tmpconfig = '/tmp/emuconfig.tmp'
		self.setTitle(_("Please wait"))
		self["status"] = StaticText()
		self["status"].text = _("Processing...")
		for emufiles in range(len(EMU)):
			if emuname[emufiles] in config.plugins.etools.activeemu.value.split()[0].lower():
				self.mainconfig = EMU[emufiles]
		if len(self.mainconfig) < 1:
			self.close()
		if fileExists('%s.second' % self.mainconfig[0]):
			for i in range(len(self.mainconfig)):
				if fileExists('%s.second' % self.mainconfig[i]):
					copyfile('%s.second' % self.mainconfig[i], '%s' % self.tmpconfig)
					copyfile('%s' % self.mainconfig[i], '%s.second' % self.mainconfig[i])
					copyfile('%s' % self.tmpconfig, '%s' % self.mainconfig[i])
			self.iConsole.ePopen('sleep 2', self.restartemu)
		else:
			self["status"].text = _("Second config not found...")
			self.iConsole.ePopen("sleep 2", self.cancelop)
	
	def restartemu(self, result, retval, extra_args):
		if config.plugins.etools.needrestartemu.value:
			self.session.openWithCallback(self.cancel, qemurestart)
		else:
			self.close()
			
	def cancelop(self, result, retval, extra_args):
		self.close()
		
	def cancel(self):
		self.close()
######################################################################################
class switch2hdmiin(Screen):
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.session = session
		self.lasttvsevice = config.tv.lastservice.value
		self.reftozap = '8192:0:1:0:0:0:0:0:0:0:'
		csref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		if csref is not None:
			if not csref.toString().startswith("4097:0:0:0:0:0:0:0:0:0:/"):
				if not csref.toString().startswith("8192"):
					self.session.nav.playService(eServiceReference(self.reftozap))
					config.plugins.etools.hdmiinonoff.value = _("Off")
				else:
					self.session.nav.playService(eServiceReference(self.lasttvsevice))
					config.plugins.etools.hdmiinonoff.value = _("On")
				config.plugins.etools.hdmiinonoff.save()
				from Components.PluginComponent import plugins
				plugins.reloadPlugins()
		self.close()
######################################################################################
class ac3dwnmix(Screen):
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.session = session
		self.iConsole = iConsole()
		self.setTitle(_("Please wait"))
		self["status"] = StaticText()
		self.showtxt = ''
		self.skin = SKIN_DWN
		if config.av.downmix_ac3.value == False or config.av.downmix_ac3.value == True:
			if config.av.downmix_ac3.value == False:
				config.av.downmix_ac3.value = True
				config.plugins.etools.ac3state.value = _("Off")
				self.showtxt = _("On")
			else:
				config.av.downmix_ac3.value = False
				config.plugins.etools.ac3state.value = _("On")
				self.showtxt = _("Off")
			config.av.downmix_ac3.save()
		else:
			if config.av.downmix_ac3.value == "passthrough":
				config.av.downmix_ac3.value = "downmix"
				config.av.downmix_dts.value = "downmix"
				config.plugins.etools.ac3state.value = _("Off")
				self.showtxt = _("On")
			else:
				config.av.downmix_ac3.value = "passthrough"
				config.av.downmix_dts.value = "passthrough"
				config.plugins.etools.ac3state.value = _("On")
				self.showtxt = _("Off")
			config.av.downmix_ac3.save()
			config.av.downmix_dts.save()

		from Components.PluginComponent import plugins
		plugins.reloadPlugins()
		self["status"].text = _("AC3,DTS downmix is %s" % self.showtxt)
		self.iConsole.ePopen('sleep 3', self.cancel)
		
	def cancel(self, result, retval, extra_args):
		self.close()
######################################################################################
class BouquetsReload(Screen):
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.session = session
		self.skin = SKIN_DWN
		
		self.setTitle(_("Please wait"))
		self["status"] = StaticText()
		self.iConsole = iConsole()
		self["status"].text = _("Reloading %s" % USERBQ[int(config.plugins.etools.reloads.value)])
		self.iConsole.ePopen('wget -q -O - http://root@127.0.0.1/web/servicelistreload?mode=%s && sleep 3' % config.plugins.etools.reloads.value, self.cancel)
		
	def cancel(self, result, retval, extra_args):
		self.close(False)		
######################################################################################
SKIN_SWP = """
	<screen name="ESwapScreen2" position="center,220" size="1125,610" title="">
	<widget source="menu" render="Listbox" position="20,10" size="1080,225" scrollbarMode="showOnDemand">
		<convert type="TemplatedMultiContent">
			{"template": [
				MultiContentEntryText(pos = (105, 3), size = (975, 38), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the Menu Titel
				MultiContentEntryText(pos = (120, 43), size = (945, 24), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
				MultiContentEntryPixmapAlphaTest(pos = (7, 7), size = (75, 60), png = 2), # index 4 is the pixmap
				],
			"fonts": [gFont("Regular", 32),gFont("Regular", 23)],
			"itemHeight": 75
			}
		</convert>
	</widget>
	<ePixmap position="20,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	</screen>"""
######################################################################################
class ESwapScreen2(Screen):
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_SWP
		self.setTitle(_("E-Swap"))
		self.iConsole = iConsole()
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"ok": self.Menu,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
		})
		self["key_red"] = StaticText(_("Close"))
		self.list = []
		self["menu"] = List(self.list)
		self.Menu()
		
	def del_fstab_swap(self, result, retval, extra_args):
		if retval == 0:
			remove_line('/etc/fstab', 'swap')
		
	def Menu(self):
		self.list = []
		minispng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/swap_off.png"))
		minisonpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/swap_on.png"))

		for line in mountp():
			if "/tmp/" not in line and "/usr/share/enigma2/" not in line and "/etc/enigma2/" not in line:
				try:
					if self.swapiswork() in line:
						self.list.append((_("Manage Swap on %s") % line, _("Start, Stop, Create, Remove Swap file"), minisonpng, line))
					else:
						self.list.append((_("Manage Swap on %s") % line, _("Start, Stop, Create, Remove Swap file"), minispng, line))
				except:
					self.list.append((_("Manage Swap on %s") % line, _("Start, Stop, Create, Remove Swap file"), minispng, line))
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.MenuDo, "cancel": self.close}, -1)

	def swapiswork(self):
		if fileExists("/proc/swaps"):
			for line in open("/proc/swaps"):
				if "media" in line:
					return line.split()[0][:-9]
		else:
			return " "
		
	def MenuDo(self):
		try:
			swppath = self["menu"].getCurrent()[3] + "swapfile"
		except:
			return
		self.session.openWithCallback(self.Menu,ESwapScreen, swppath)
	
	def exit(self):
		if self.swapiswork() == " ":
			remove_line('/etc/fstab', 'swap')
		self.close()
######################################################################################
class ESwapScreen(Screen):
	def __init__(self, session, swapdirect):
		self.swapfile = swapdirect
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_SWP
		self.setTitle(_("E-Swap"))
		self.iConsole = iConsole()
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"ok": self.CfgMenuDo,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
		})
		self["key_red"] = StaticText(_("Close"))
		self.list = []
		self["menu"] = List(self.list)
		self.CfgMenu()

	def isSwapPossible(self):
		for line in open("/proc/mounts"):
			fields= line.rstrip('\n').split()
			if fields[1] == "%s" % self.swapfile[:-9]:
				if fields[2] == 'ext2' or fields[2] == 'ext3' or fields[2] == 'ext4' or fields[2] == 'vfat':
					return True
				else:
					return False
		return False
		
	def isSwapRun(self):
		if fileExists('/proc/swaps'):
			for line in open('/proc/swaps'):
				if self.swapfile in line:
					return True
			return False
		else:
			return False
			
	def isSwapSize(self):
		if fileExists(self.swapfile):
			swapsize = os.path.getsize(self.swapfile) / 1048576
			return ("%sMb" % swapsize)
		else:
			return ("N/A Mb")

	def createSwapFile(self, size):
		self.session.openWithCallback(self.CfgMenu, create_swap, self.swapfile, size)

	def removeSwapFle(self):
		self.iConsole.ePopen("rm -f %s" % self.swapfile, self.info_mess, _("Swap file removed"))

	def info_mess(self, result, retval, extra_args):
		self.setTitle(_("Swap on mount device"))
		if retval == 0:
			self.mbox = self.session.open(MessageBox,extra_args, MessageBox.TYPE_INFO, timeout = 3 )
		else:
			self.mbox = self.session.open(MessageBox,_("Failure..."), MessageBox.TYPE_INFO, timeout = 3)
		self.CfgMenu()

	def offSwapFile_step1(self):
		remove_line('/etc/fstab', 'swap')
		self.iConsole.ePopen("swapoff %s" % self.swapfile, self.info_mess, _("Swap file stoped"))

	def onSwapFile_step1(self):
		self.iConsole.ePopen("swapoff %s" % self.swapfile, self.onSwapFile_step2)
		
	def onSwapFile_step2(self, result, retval, extra_args):
		remove_line('/etc/fstab', 'swap')
		with open('/etc/fstab', 'a') as fsatb_file:
			fsatb_file.write('%s swap swap defaults 0 0\n' % self.swapfile)
			fsatb_file.close()
		self.iConsole.ePopen("swapon %s" % self.swapfile, self.info_mess,_("Swap file started"))

	def CfgMenu(self):
		self.list = []
		minispng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/swap_off.png"))
		minisonpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/swap_on.png"))
		if self.isSwapPossible():
			if os.path.exists(self.swapfile):
				if self.isSwapRun():
					self.list.append((_("Swap off"), 1, (_("Swap on %s off (%s)") % (self.swapfile.replace("/swapfile", ""), self.isSwapSize())), minisonpng))
				else:
					self.list.append((_("Swap on"), 2, (_("Swap on %s on (%s)") % (self.swapfile.replace("/swapfile", ""), self.isSwapSize())), minispng))
					self.list.append((_("Remove swap"),3, (_("Remove swap on %s (%s)") % (self.swapfile.replace("/swapfile", ""), self.isSwapSize())), minispng))
			else:
				self.list.append((_("Make swap"), 4, _("Make swap on %s (256MB)") % self.swapfile.replace("/swapfile", ""), minispng))
				self.list.append((_("Make swap"), 5, _("Make swap on %s (512MB)") % self.swapfile.replace("/swapfile", ""), minispng))
				self.list.append((_("Make swap"), 6, _("Make swap on %s (1024MB)") % self.swapfile.replace("/swapfile", ""), minispng))
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.CfgMenuDo, "cancel": self.close}, -1)
			
	def CfgMenuDo(self):
		self.setTitle(_("Please wait"))
		if self.isSwapPossible():
			item = self["menu"].getCurrent()[1]
			if item == 1:
				self.offSwapFile_step1()
			elif item == 2:
				self.onSwapFile_step1()
			elif item == 3:
				self.removeSwapFle()
			elif item == 4:
				self.createSwapFile("256")
			elif item == 5:          
				self.createSwapFile("512")
			elif item == 6:
				self.createSwapFile("1024")
			
		self.CfgMenu()
			
	def exit(self):
		self.close()
######################################################################################
class create_swap(Screen):
	def __init__(self, session, swapfile, size):
		Screen.__init__(self, session)
		self.session = session
		self.skin = SKIN_DWN
		self.swapfile = swapfile
		self.size = size
		self.setTitle(_("Please wait"))
		self["status"] = StaticText()
		self.iConsole = iConsole()
		self["status"].text = _("Creating...")
		self.iConsole.ePopen("dd if=/dev/zero of=%s bs=1M count=%s" % (self.swapfile, self.size), self.makeSwapFile)
		
	def makeSwapFile(self, result, retval, extra_args):
		if retval == 0:
			self.iConsole.ePopen("mkswap %s" % self.swapfile, self.info_mess)
		else:
			self["status"].text = _("Failure...")
			self.iConsole.ePopen("sleep 3", self.end_func)
			
	def info_mess(self, result, retval, extra_args):
		if retval == 0:
			self["status"].text = _("Success...")
			self.iConsole.ePopen("sleep 3", self.end_func)
		else:
			self["status"].text = _("Failure...")
			self.iConsole.ePopen("sleep 3", self.end_func)

	def end_func(self, result, retval, extra_args):
		self.close()
######################################################################################
SKIN_SCRP2 = """
<screen name="EScriptScreen2" position="center,220" size="1125,610" title="">
	<widget source="menu" render="Listbox" position="20,10" size="1080,225" scrollbarMode="showOnDemand">
		<convert type="TemplatedMultiContent">
			{"template": [
				MultiContentEntryText(pos = (105, 3), size = (975, 38), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the Menu Titel
				MultiContentEntryText(pos = (120, 43), size = (945, 24), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
				MultiContentEntryPixmapAlphaTest(pos = (7, 7), size = (75, 60), png = 2), # index 4 is the pixmap
				],
			"fonts": [gFont("Regular", 32),gFont("Regular", 23)],
			"itemHeight": 75
			}
		</convert>
	</widget>
	<ePixmap position="20,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/green.png" transparent="1" alphatest="on" />
	<ePixmap position="526,590" zPosition="1" size="280,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/yellow.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_green" render="Label" position="273,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_yellow" render="Label" position="526,545" zPosition="2" size="280,45" valign="center" halign="center" font="Regular;30" transparent="1" />
</screen>"""
######################################################################################	
class EScriptScreen2(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.skin = SKIN_SCRP2
		self.script, self.name = '', ''
		self.path = config.plugins.etools.scriptpath.value
		self.setTitle(_("E-Script executer (%s)" % config.plugins.etools.scriptpath.value))
		self.iConsole = iConsole()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Run"))
		self["key_yellow"] = StaticText(_("ShadowRun"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"back": self.close,
			"red": self.close,
			"green": self.run,
			"ok": self.run,
			"yellow": self.shadowrun,
			})
		self.list = []
		self["menu"] = List(self.list)
		self.scrpit_menu()
		
	def scrpit_menu(self):
		self.list = []
		chfile = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/shcrpt.png"))
		pyfile = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/pycrpt.png"))
		if pathExists(self.path):
			for line in os.listdir(self.path):
				try:
					if line.endswith(".sh"):
						self.list.append((line,"%d Kb, %s" % (os.path.getsize(self.path + line) / 1024, time.ctime(os.path.getctime(self.path + line))), chfile))
					elif line.endswith(".py"):
						self.list.append((line,"%d Kb, %s" % (os.path.getsize(self.path + line) / 1024, time.ctime(os.path.getctime(self.path + line))), pyfile))
				except Exception as e:
					now = time.localtime(time.time())
					logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))
		self.list.sort()
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], { "cancel": self.close}, -1)

	def shadowrun(self):
		try:
			self.script = self["menu"].getCurrent()[0]
			if self.script is not None:
				self.name = "%s%s" % (config.plugins.etools.scriptpath.value, self.script)
				if self.name.endswith('.sh'):
					os.chmod('%s' %  self.name, 755)
				else:
					self.name = 'python %s' % self.name
				self.iConsole.ePopen("nohup %s >/dev/null &" %  self.name)
				self.mbox = self.session.open(MessageBox,(_("the script is running in the background...")), MessageBox.TYPE_INFO, timeout = 3 )
		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))
			
	def run(self):
		try:
			self.script = self["menu"].getCurrent()[0]
			if self.script is not None:
				self.name = "%s%s" % (config.plugins.etools.scriptpath.value, self.script)
				if self.name.endswith('.sh'):
					os.chmod('%s' %  self.name, 755)
				else:
					self.name = 'python %s' % self.name
				self.session.open(Console, self.script, cmdlist=[self.name])
		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))
######################################################################################
SKIN_CRASH = """
<screen name="eCrashLogScreen" position="center,220" size="1125,610" title="">
	<widget source="menu" render="Listbox" position="20,10" size="1080,225" scrollbarMode="showOnDemand">
		<convert type="TemplatedMultiContent">
			{"template": [
				MultiContentEntryText(pos = (105, 3), size = (975, 38), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the Menu Titel
				MultiContentEntryText(pos = (120, 43), size = (945, 24), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
				MultiContentEntryPixmapAlphaTest(pos = (7, 7), size = (75, 60), png = 2), # index 4 is the pixmap
				],
			"fonts": [gFont("Regular", 32),gFont("Regular", 23)],
			"itemHeight": 75
			}
		</convert>
	</widget>
	<ePixmap position="20,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/green.png" transparent="1" alphatest="on" />
	<ePixmap position="526,590" zPosition="1" size="280,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/yellow.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_green" render="Label" position="273,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_yellow" render="Label" position="526,545" zPosition="2" size="280,45" valign="center" halign="center" font="Regular;30" transparent="1" />
</screen>"""
######################################################################################
class eCrashLogScreen(Screen):
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_CRASH
		self.iConsole = iConsole()
		self.item = ''
		self.path = config.plugins.etools.crashpath.value
		self.setTitle(_("E-Crash Viewer (%s) (press [info] for --remove mode change)" % config.plugins.etools.crashpath.value.rstrip('/')))
		self.session = session
		self.forcecommand = FORCEREMOVE
		self.forcemode = config.plugins.etools.crashremmode.value
		self.current_index = self.forcecommand.index(self.forcemode)
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions", "EPGSelectActions", "SetupActions"],
		{
			"back": self.close,
			"red": self.close,
			"green": self.Ok,
			"ok": self.Ok,
			"yellow": self.YellowKey,
			"info": self.infoKey,
			})
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("View"))
		self["key_yellow"] = StaticText(_("%s" % config.plugins.etools.crashremmode.value))
		self.list = []
		self["menu"] = List(self.list)
		self.FileMenu()
		
	def infoKey(self):
		self.current_index = self.current_index + 1
		if self.current_index == len(self.forcecommand):
			self.current_index = 0
		self.forcemode = self.forcecommand[self.current_index]
		config.plugins.etools.crashremmode.value = self.forcemode
		config.plugins.etools.crashremmode.save()
		self["key_yellow"].setText(_("%s") % self.forcemode)
		
	def FileMenu(self):
		self.list = []
		minipng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/crash.png"))
		if pathExists(self.path):
			for line in os.listdir(self.path):
				if line.startswith('enigma2_crash') or line.endswith('-enigma-crash.log'):
					try:
						self.list.append((line,"%s" % time.ctime(os.path.getctime(self.path + line)), minipng))
					except Exception as e:
						now = time.localtime(time.time())
						logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))
		self.list.sort()
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], { "cancel": self.close}, -1)
		
	def Ok(self):
		try:
			if self["menu"].getCurrent()[0] is not None:
				self.item = self.path + self["menu"].getCurrent()[0]
				self.session.open(fullLogScreen, self.item)
		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))
	
	def YellowKey(self):
		try:
			if self["menu"].getCurrent()[0] is not None:
				self.item = self.path + self["menu"].getCurrent()[0]
				if self.forcemode == self.forcecommand[0]:
					if fileExists(self.item):
						self.iConsole.ePopen('rm -f %s' % self.item, self.finish)
				else:
					if fileExists(self.item):
						self.iConsole.ePopen('rm -f %s*crash*.log' % config.plugins.etools.crashpath.value, self.finish)

		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))
		self.FileMenu()
		
	def finish(self, result, retval, extra_args):
		if self.forcemode == self.forcecommand[0]:
			self.mbox = self.session.open(MessageBox,(_("removed %s") % self.item), MessageBox.TYPE_INFO, timeout = 2 )
		else:
			self.mbox = self.session.open(MessageBox,(_("removed all crashlog files")), MessageBox.TYPE_INFO, timeout = 2 )
		self.FileMenu()
######################################################################################
SKIN_CRASHLOG = """
<screen name="fullLogScreen" position="50,175" size="1820,800" title="">
	<ePixmap position="20,790" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,790" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/blue.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,745" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_blue" render="Label" position="273,745" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget name="text" position="10,10" size="1800,712" font="Console; 30" />
</screen>"""
######################################################################################
class fullLogScreen(Screen):
	def __init__(self, session, what):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_CRASHLOG
		self.crashfile = what
		self.setTitle(_("E-Crash (%s)" % self.crashfile.split('/')[-1]))
		self["key_red"] = StaticText(_("Close"))
		self["key_blue"] = StaticText(_("Restart"))
		self["text"] = ScrollLabel("")
		self.listcrah()
		
	def exit(self):
		self.close()
		
	def restart_enigma(self):
		self.session.open(TryQuitMainloop, 3)
		
	def listcrah(self):
		list = ""
		with open(self.crashfile, "r") as files:
			for line in files:
				if "Traceback (" in line or line.startswith("PC:"):
					list += line
					for line in files:
						list += line
						if line.startswith("]]>") or line.startswith("dmesg"):
							break
		self["text"].setText(list)
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ShortcutActions", "WizardActions"], 
		{ 
		"cancel": self.close,
		"back": self.close,
		"up": self["text"].pageUp,
		"left": self["text"].pageUp,
		"down": self["text"].pageDown,
		"right": self["text"].pageDown,
		"red": self.close,
		"blue": self.restart_enigma,
		}, -1)
######################################################################################
SKIN_CRON = """
<screen name="CrontabMan" position="center,220" size="1125,610" title="">
	<ePixmap position="20,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/green.png" transparent="1" alphatest="on" />
	<ePixmap position="526,590" zPosition="1" size="280,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/yellow.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_green" render="Label" position="273,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_yellow" render="Label" position="526,545" zPosition="2" size="280,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="menu" render="Listbox" position="20,10" size="1080,225" scrollbarMode="showOnDemand">
	<convert type="TemplatedMultiContent">
	{"template": [
		MultiContentEntryText(pos = (15, 3), size = (1065, 35), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
			],
	"fonts": [gFont("Regular", 30),gFont("Regular", 24)],
	"itemHeight": 48
	}
			</convert>
		</widget>
</screen>"""
######################################################################################
class CrontabMan(Screen):
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_CRON
		self.path = cronpath()
		self.setTitle(_("E-Cron Editor - %s") % self.path)
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"ok": self.Ok,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"green": self.GreenKey,
			"yellow": self.YellowKey,
		})
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Add tabs"))
		self["key_yellow"] = StaticText(_("Remove tabs"))
		self.list = []
		self["menu"] = List(self.list)
		self.cMenu()
		
	def cMenu(self):
		self.list = []
		if fileExists(self.path):
			for line in open(self.path):
				self.list.append((line, 0))
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.Ok, "cancel": self.close}, -1)

	def Ok(self):
		self.close()
		
	def GreenKey(self):
		self.session.openWithCallback(self.cMenu, CrontabManAdd)
	
	def YellowKey(self):
		try:
			remove_line(self.path, self["menu"].getCurrent()[0])
		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))
		with open('%scron.update' % self.path[:-4], 'w') as cron_update:
			cron_update.write('root')
			cron_update.close()
		self.cMenu()
		
	def exit(self):
		self.close()
######################################################################################
SKIN_CRONADD = """
<screen name="CrontabManAdd" position="center,220" size="1125,610" title="">
	<widget name="config"  position="20,10" size="1080,480" itemHeight="48" font="Regular;30" scrollbarMode="showOnDemand" />
	<ePixmap position="20,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,590" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/green.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_green" render="Label" position="273,545" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
</screen>"""
######################################################################################
class CrontabManAdd(ConfigListScreen, Screen):
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_CRONADD
		self.iConsole = iConsole()
		self.path = cronpath()
		self.setTitle(_("E-Cron Editor - %s") % self.path)
		self.list = []
		self.list.append(getConfigListEntry(_("Min"), config.plugins.etools.min))
		self.list.append(getConfigListEntry(_("Hour"), config.plugins.etools.hour))
		self.list.append(getConfigListEntry(_("Day of month"), config.plugins.etools.dayofmonth))
		self.list.append(getConfigListEntry(_("Month"), config.plugins.etools.month))
		self.list.append(getConfigListEntry(_("Day of week"), config.plugins.etools.dayofweek))
		self.list.append(getConfigListEntry(_("Command"), config.plugins.etools.command))
		self.list.append(getConfigListEntry(_("Every"), config.plugins.etools.every))
		ConfigListScreen.__init__(self, self.list)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Add"))
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.cancel,
			"cancel": self.cancel,
			"green": self.ok,
			"ok": self.ok
		}, -2)
		
	def cancel(self):
		for i in self["config"].list:
			i[1].cancel()
		self.close()
		
	def ok(self):
		if not fileExists(self.path):
			open(self.path, 'a').close()
		everymin = everyhour = everydayofmonth = everymonth = everydayofweek = ""
		if config.plugins.etools.min.value != '*' and config.plugins.etools.every.value == '1':
			everymin = '*/'
		elif config.plugins.etools.hour.value != '*' and config.plugins.etools.every.value == '2':
			everyhour = '*/'
		elif config.plugins.etools.dayofmonth.value != '*' and config.plugins.etools.every.value == '3':
			everydayofmonth = '*/'
		elif config.plugins.etools.month.value != '*' and config.plugins.etools.every.value == '4':
			everymonth = '*/'
		elif config.plugins.etools.dayofweek.value != '*' and config.plugins.etools.every.value == '5':
			everydayofweek = '*/'
		if config.plugins.etools.min.value == '*' and config.plugins.etools.hour.value == '*' and config.plugins.etools.dayofmonth.value == '*' and config.plugins.etools.month.value == '*' and  config.plugins.etools.dayofweek.value == '*':
			print ("error")
		else:
			with open(self.path, 'a') as cron_root:
				cron_root.write('%s%s %s%s %s%s %s%s %s%s    %s' % (everymin, config.plugins.etools.min.value, everyhour, config.plugins.etools.hour.value,\
					everydayofmonth, config.plugins.etools.dayofmonth.value, everymonth, config.plugins.etools.month.value,\
					everydayofweek, config.plugins.etools.dayofweek.value, config.plugins.etools.command.value))
				cron_root.close()
			with open('%scron.update' % self.path[:-4], 'w') as cron_update:
				cron_update.write('root')
				cron_update.close()
		for i in self["config"].list:
			i[1].cancel()
		self.close()
######################################################################################
SKIN_IF = """
<screen name="InstallFeed" position="397,220" size="1125,750" title="">
	<widget source="menu" render="Listbox" position="25,10" size="1080,675" scrollbarMode="showOnDemand">
		<convert type="TemplatedMultiContent">
			{"template": [
				MultiContentEntryText(pos = (105, 3), size = (975, 38), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the Menu Titel
				MultiContentEntryText(pos = (120, 43), size = (945, 30), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
				MultiContentEntryPixmapAlphaTest(pos = (7, 7), size = (75, 60), png = 2), # index 4 is the pixmap
				],
			"fonts": [gFont("Regular", 32),gFont("Regular", 23)],
			"itemHeight": 75
			}
		</convert>
	</widget>
	<ePixmap position="20,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/green.png" transparent="1" alphatest="on" />
	<ePixmap position="526,590" zPosition="1" size="280,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/blue.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_green" render="Label" position="273,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_blue" render="Label" position="526,545" zPosition="2" size="280,45" valign="center" halign="center" font="Regular;30" transparent="1" />
</screen>"""
class InstallFeed(Screen):	  
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.skin = SKIN_IF
		self.forcefilter = config.plugins.etools.filtername.value
		if self.forcefilter == "0":
			self.setTitle(_("E-Feed Installer (press [info] to filter)"))
		else:
			self.setTitle(_("E-Feed Installer (%s) (press [info] to filter)" % self.forcefilter.rstrip('-')))
		self.forcecommand = FEEDFILTERQ
		self.current_index = self.forcecommand.index(self.forcefilter)
		self.session = session
		self.onepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/ipk_off.png"))
		self.curpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/ipk_on.png"))
		self.indexpos = None
		self.path = status_path()
		BKEYS = {
				"cancel": self.cancel,
				"ok": self.setup,
				"red": self.cancel,
				"green": self.setup,
				"blue": self.restart_enigma,
				"info": self.infoKey,
			}
		self.list = []
		self["menu"] = List(self.list)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "EPGSelectActions", "WizardActions", "SetupActions"], BKEYS, -1)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText("Install")
		self["key_blue"] = StaticText("Restart")
		self.feedlist()
		
	def infoKey(self):
		self.current_index = self.current_index + 1
		if self.current_index == len(self.forcecommand):
			self.current_index = 0
		self.forcefilter = self.forcecommand[self.current_index]
		if self.forcefilter == "0":
			self.setTitle(_("E-Feed Installer (press [info] to filter)"))
		else:
			self.setTitle(_("E-Feed Installer (%s) (press [info] to filter)" % self.forcefilter.rstrip('-')))
		self["menu"].setIndex(0)
		config.plugins.etools.filtername.value = self.forcefilter
		config.plugins.etools.filtername.save()
		self.feedlist()

	def restart_enigma(self):
		self.session.open(TryQuitMainloop, 3)
			
	def feedlist(self):
		self.list = []
		pkg_name = pkg_desc = ' '
		statuspath = ''
		list = os.listdir(self.path[:-7])
		if len(list) < 5:
			list = os.listdir(self.path[:-7] + '/lists')
			statuspath = self.path[:-6] + 'lists/'
		else:
			statuspath = self.path[:-6]
		for file in list:
			if os.path.isfile(statuspath + file):
				if not file == 'status':
					for line in open(statuspath + file):
						if 'Package:' in line:
							pkg_name = line.split(':')[1]
						elif 'Description:' in line:
							pkg_desc = line.split(':')[1]
							if self.forcefilter != "0":
								if self.forcefilter in pkg_name:
									self.list.append((pkg_name, pkg_desc.replace('"', ''), self.onepng))
							else:
								self.list.append((pkg_name, pkg_desc.replace('"', ''), self.onepng))
		self.list.sort()
		self["menu"].setList(self.list)
		
	def cancel(self):
		self.close()

	def setup(self):
		try:
			self.session.open(Console, title = _("Install extensions from feed"), cmdlist = ["opkg install %s" % self["menu"].getCurrent()[0]], closeOnSuccess = False)
		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))
########################################################################################################
SKIN_RM = """
<screen name="eRemoveIPK"  position="397,220" size="1125,750" title="">
	<widget source="menu" render="Listbox" position="25,10" size="1080,675" scrollbarMode="showOnDemand">
		<convert type="TemplatedMultiContent">
			{"template": [
				MultiContentEntryText(pos = (105, 3), size = (975, 38), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the Menu Titel
				MultiContentEntryText(pos = (120, 43), size = (945, 30), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
				MultiContentEntryPixmapAlphaTest(pos = (7, 7), size = (75, 60), png = 2), # index 4 is the pixmap
				],
			"fonts": [gFont("Regular", 32),gFont("Regular", 23)],
			"itemHeight": 75
			}
		</convert>
	</widget>
	<ePixmap position="20,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/green.png" transparent="1" alphatest="on" />
	<ePixmap position="526,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/yellow.png" transparent="1" alphatest="on" />
	<ePixmap position="779,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/blue.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_green" render="Label" position="273,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_yellow" render="Label" position="526,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_blue" render="Label" position="779,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
</screen>"""
class eRemoveIPK(Screen):	  
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.skin = SKIN_RM	
		self.forcefilter = config.plugins.etools.filterrm.value
		if self.forcefilter == "0":
			self.setTitle(_("E-Remover (press [info] to filter)"))
		else:
			self.setTitle(_("E-Remover (%s) (press [info] to filter)" % self.forcefilter.rstrip('-')))
		self.forcecommand = FEEDFILTERQ
		self.current_index = self.forcecommand.index(self.forcefilter)
		self.session = session
		self.path = status_path()
		self.iConsole = iConsole()
		self.status = False
		self.onepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/ipk_off.png"))
		self.curpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/ipk_on.png"))
		BKEYS = {
				"cancel": self.cancel,
				"ok": self.remove_ipk,
				"green": self.remove_ipk,
				"red": self.cancel,
				"yellow": self.adv_remove,
				"blue": self.restart_enigma,
				"info": self.infoKey,
			}
		self.list = []
		self.list_tmp = []
		self["menu"] = List(self.list)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "EPGSelectActions", "WizardActions", "SetupActions"], BKEYS, -1)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Remove"))
		self["key_yellow"] = StaticText(_("force Remove"))
		self["key_blue"] = StaticText(_("Restart"))
		self.feedlist()
		
	def infoKey(self):
		self.current_index = self.current_index + 1
		if self.current_index == len(self.forcecommand):
			self.current_index = 0
		self.forcefilter = self.forcecommand[self.current_index]
		if self.forcefilter == "0":
			self.setTitle(_("E-Remover (press [info] to filter)"))
		else:
			self.setTitle(_("E-Remover (%s) (press [info] to filter)" % self.forcefilter.rstrip('-')))
		self["menu"].setIndex(0)
		config.plugins.etools.filterrm.value = self.forcefilter
		config.plugins.etools.filterrm.save()
		self.feedlist()

	def feedlist(self):
		self.list = []
		for line in open(status_path()):
			if "Package:" in line:
				pkg_name = line.replace("\n","").split()[-1]
			elif "Version:" in line:
				pkg_desc = line.split()[-1] + "\n"
			elif "Status:" in line and not "not-installed" in line:
				if self.forcefilter != "0":
					if self.forcefilter in pkg_name:
						self.list.append((pkg_name, pkg_desc, self.onepng))
				else:
					self.list.append((pkg_name, pkg_desc, self.onepng))
		self.list.sort()
		self.list_tmp = self.list
		self["menu"].setList(self.list)

	def cancel(self):
		self.close()
	
	def restart_enigma(self):
		self.session.open(TryQuitMainloop, 3)
		
	def remove_ipk(self):
		local_status = ipk_dir = ''
		try:
			pkg_name = self["menu"].getCurrent()[0]
			self.list_tmp.remove(self["menu"].getCurrent())
			if self.status:
				local_status = '-force-remove'
				self.staus = False
			if 'plugin' in pkg_name or 'skin' in pkg_name:
				if fileExists('%s%s.list' % (self.path[:-6] + 'info/', pkg_name)):
					for line in open('%s%s.list' % (self.path[:-6] + 'info/', pkg_name)):
						if 'plugin.py' in line or 'plugin.pyo' in line or 'plugin.pyc' in line:
							ipk_dir = line[:-10]
						elif 'skin.xml' in line:
							ipk_dir = line[:-9]
			self.session.open(Console, title = _("%s" % ipk_dir), cmdlist = ["opkg remove %s %s" % (local_status, pkg_name)], closeOnSuccess = False)
			if pathExists(ipk_dir):
				self.iConsole.ePopen("rm -rf %s" % ipk_dir)
			self.list = list(self.list_tmp)
			self["menu"].updateList(self.list)
		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))

	def adv_remove(self):
		self.staus = True
		self.remove_ipk()
######################################################################################
SKIN_DF = """
<screen name="eDownloadFeed" position="397,220" size="1125,750" title="">
	<widget source="menu" render="Listbox" position="25,10" size="1080,675" scrollbarMode="showOnDemand">
		<convert type="TemplatedMultiContent">
			{"template": [
				MultiContentEntryText(pos = (105, 3), size = (975, 38), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the Menu Titel
				MultiContentEntryText(pos = (120, 43), size = (945, 30), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
				MultiContentEntryPixmapAlphaTest(pos = (7, 7), size = (75, 60), png = 2), # index 4 is the pixmap
				],
			"fonts": [gFont("Regular", 32),gFont("Regular", 23)],
			"itemHeight": 75
			}
		</convert>
	</widget>
	<ePixmap position="20,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/green.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_green" render="Label" position="273,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
</screen>"""
######################################################################################
class eDownloadFeed(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skin = SKIN_DF
		self.forcefilter = config.plugins.etools.filterdw.value
		if self.forcefilter == "0":
			self.setTitle(_("E-Feed Downloader (press [info] to filter)"))
		else:
			self.setTitle(_("E-Feed Downloader (%s) (press [info] to filter)" % self.forcefilter.rstrip('-')))
		self.forcecommand = FEEDFILTERQ
		self.current_index = self.forcecommand.index(self.forcefilter)
		self.session = session
		self.path = status_path()
		self.onepng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/ipk_off.png"))
		self.curpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/ipk_on.png"))
		BKEYS = {
				"cancel": self.cancel,
				"ok": self.download,
				"green": self.download,
				"red": self.cancel,
				"info": self.infoKey,
			}
		if fileExists(self.path[:-6] + 'status'):
			enigma.eConsoleAppContainer().execute('mv %s %s.tmp' %(self.path[:-6] + 'status', self.path[:-6] + 'status'))
		self.list = []
		self["menu"] = List(self.list)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "EPGSelectActions", "WizardActions", "SetupActions"], BKEYS, -1)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Download"))
		self.feedlist()
		
	def infoKey(self):
		self.current_index = self.current_index + 1
		if self.current_index == len(self.forcecommand):
			self.current_index = 0
		self.forcefilter = self.forcecommand[self.current_index]
		if self.forcefilter == "0":
			self.setTitle(_("E-Feed Downloader (press [info] to filter)"))
		else:
			self.setTitle(_("E-Feed Downloader (%s) (press [info] to filter)" % self.forcefilter.rstrip('-')))
		self["menu"].setIndex(0)
		config.plugins.etools.filterdw.value = self.forcefilter
		config.plugins.etools.filterdw.save()
		self.feedlist()

	def feedlist(self):
		self.list = []
		pkg_name = pkg_desc = ' '
		statuspath = ''
		list = os.listdir(self.path[:-7])
		if len(list) < 5:
			list = os.listdir(self.path[:-7] + '/lists')
			statuspath = self.path[:-6] + 'lists/'
		else:
			statuspath = self.path[:-6]
		for file in list:
			if os.path.isfile(statuspath + file):
				if not file == 'status':
					for line in open(statuspath + file):
						if 'Package:' in line:
							pkg_name = line.split(':')[1]
						elif 'Description:' in line:
							pkg_desc = line.split(':')[1]
							if self.forcefilter != "0":
								if self.forcefilter in pkg_name:
									self.list.append((pkg_name, pkg_desc.replace('"', ''), self.onepng))
							else:
								self.list.append((pkg_name, pkg_desc.replace('"', ''), self.onepng))
		self.list.sort()
		self["menu"].setList(self.list)
		
	def download(self):
		try:
			self.session.open(Console, title = _("Download extensions from feed"), cmdlist = ["cd /tmp && opkg download %s" % self["menu"].getCurrent()[0]], closeOnSuccess = False)
		except Exception as e:
			now = time.localtime(time.time())
			logging('%02d:%02d:%d %02d:%02d:%02d - %s\r\n' % (now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec, str(e)))
			
	def cancel(self):
		if fileExists(self.path[:-6] + 'status.tmp'):
			enigma.eConsoleAppContainer().execute("mv %s.tmp %s" %(self.path[:-6] + 'status', self.path[:-6] + 'status'))
		self.close()
######################################################################################		
SKIN_KLM = """
<screen name="eKernel"  position="397,220" size="1125,750" title="">
	<widget source="menu" render="Listbox" position="25,10" size="1080,675" scrollbarMode="showOnDemand">
		<convert type="TemplatedMultiContent">
			{"template": [
				MultiContentEntryText(pos = (105, 3), size = (975, 38), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the Menu Titel
				MultiContentEntryText(pos = (120, 43), size = (945, 30), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
				MultiContentEntryPixmapAlphaTest(pos = (7, 7), size = (75, 60), png = 2), # index 4 is the pixmap
				],
			"fonts": [gFont("Regular", 32),gFont("Regular", 23)],
			"itemHeight": 75
			}
		</convert>
	</widget>
	<ePixmap position="20,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/green.png" transparent="1" alphatest="on" />
	<ePixmap position="526,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/yellow.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_green" render="Label" position="273,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_yellow" render="Label" position="526,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
</screen>"""
######################################################################################
class eKernel(Screen):
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.iConsole = iConsole()
		self.skin = SKIN_KLM	
		self.timeout = 3
		self.index = 0
		self.runmodule = ''
		self.module_list()
		self.setTitle(_("E-Kernel module manager"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"ok": self.Ok,
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			"green": self.Ok,
			"yellow": self.YellowKey,
		})
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("load/unload"))
		self["key_yellow"] = StaticText(_("lsmod"))
		self.list = []
		self["menu"] = List(self.list)
		
	def module_list(self):
		self.iConsole.ePopen('find /lib/modules/*/kernel/drivers/ | grep .ko', self.IsRunnigModDig)
		
	def YellowKey(self):
		self.session.open(lsmodScreen)
		
	def IsRunnigModDig(self, result, retval, extra_args):
		self.iConsole.ePopen('lsmod', self.run_modules_list, result)
		
	def run_modules_list(self, result, retval, extra_args):
		self.runmodule = ''
		if retval == 0:
			for line in result.splitlines():
				self.runmodule += line.split()[0].replace('-','_') + ' '
		self.CfgMenu(extra_args)
					
	def CfgMenu(self, result):
		self.list = []
		klma = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/klma.png"))
		klm = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/klm.png"))
		if result:
			for line in result.splitlines():
				if line.split('/')[-1][:-3].replace('-','_') in self.runmodule.replace('-','_'):
					self.list.append((line.split('/')[-1], line.split('kernel')[-1], klma, line, True))
				else:
					self.list.append((line.split('/')[-1], line.split('kernel')[-1], klm, line, False))
			self["menu"].setList(self.list)
			self["menu"].setIndex(self.index)
		self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.Ok, "cancel": self.close}, -1)

	def Ok(self):
		module_name = ''
		module_name =  self["menu"].getCurrent()[-2].split('/')[-1][:-3]
		if not self["menu"].getCurrent()[-1]:
			self.load_module(module_name)
		else:
			self.unload_modele(module_name)
		self.index = self["menu"].getIndex()
		
	def unload_modele(self, module_name):
		self.iConsole.ePopen("modprobe -r %s" % module_name, self.rem_conf, module_name)
		
	def rem_conf(self, result, retval, extra_args):
		self.iConsole.ePopen('rm -f /etc/modprobe.d/%s.conf' % extra_args, self.info_mess, extra_args)
		
	def info_mess(self, result, retval, extra_args):
		self.mbox = self.session.open(MessageBox,_("unloaded %s.ko") % extra_args, MessageBox.TYPE_INFO, timeout = self.timeout )
		self.module_list()
		
	def load_module(self, module_name):
		self.iConsole.ePopen("modprobe %s" % module_name, self.write_conf, module_name)
		
	def write_conf(self, result, retval, extra_args):
		if retval == 0:
			with open('/etc/modprobe.d/%s.conf' % extra_args, 'w') as autoload_file:
				autoload_file.write('%s' % extra_args)
				autoload_file.close()
			self.mbox = self.session.open(MessageBox,_("loaded %s.ko") % extra_args, MessageBox.TYPE_INFO, timeout = self.timeout )
			self.module_list()
		
	def exit(self):
		self.close()
######################################################################################
SKIN_LSMOD = """
<screen name="lsmodScreen"  position="397,220" size="1125,750" title="">
	<widget source="menu" render="Listbox" position="25,10" size="1080,675" scrollbarMode="showOnDemand">
		<convert type="TemplatedMultiContent">
			{"template": [
				MultiContentEntryText(pos = (105, 3), size = (975, 38), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the Menu Titel
				MultiContentEntryText(pos = (120, 43), size = (945, 30), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
				MultiContentEntryPixmapAlphaTest(pos = (7, 7), size = (75, 60), png = 2), # index 4 is the pixmap
				],
			"fonts": [gFont("Regular", 32),gFont("Regular", 23)],
			"itemHeight": 75
			}
		</convert>
	</widget>
	<ePixmap position="20,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
</screen>"""
######################################################################################
class lsmodScreen(Screen):
	def __init__(self, session):
		self.session = session
		Screen.__init__(self, session)
		self.skin = SKIN_LSMOD
		self.iConsole = iConsole()
		self.setTitle(_("E-Kernel modules currently loaded (lsmod)"))
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"cancel": self.exit,
			"back": self.exit,
			"red": self.exit,
			})
		self["key_red"] = StaticText(_("Close"))
		self.list = []
		self["menu"] = List(self.list)
		self.CfgMenu()

	def CfgMenu(self):
		self.iConsole.ePopen('lsmod', self.run_modules_list)
		
	def run_modules_list(self, result, retval, extra_args):
		self.list = []
		aliasname = ''
		minipng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/klm.png"))
		if retval == 0:
			for line in result.splitlines():
				if len(line.split()) > 3:
					aliasname = line.split()[-1]
				else: 
					aliasname = ' '
				if 'Module' not in line:
					self.list.append((line.split()[0],( _("size: %3.01f Kb  %s") % (round(float(line.split()[1])/1024, 1), aliasname)), minipng)) 
		self["menu"].setList(self.list)
		self["actions"] = ActionMap(["OkCancelActions"], { "cancel": self.close}, -1)

	def exit(self):
		self.close()	
#########################################################################################################
SKIN_UPGD = """
<screen name="eupgrade"  position="397,220" size="1125,750" title="">
	<widget source="menu" render="Listbox" position="25,10" size="1080,675" scrollbarMode="showOnDemand">
		<convert type="TemplatedMultiContent">
			{"template": [
				MultiContentEntryText(pos = (105, 3), size = (975, 38), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 0 is the Menu Titel
				MultiContentEntryText(pos = (120, 43), size = (945, 30), font=1, flags = RT_HALIGN_LEFT, text = 1), # index 3 is the Description
				MultiContentEntryPixmapAlphaTest(pos = (7, 7), size = (75, 60), png = 2), # index 4 is the pixmap
				],
			"fonts": [gFont("Regular", 32),gFont("Regular", 23)],
			"itemHeight": 75
			}
		</convert>
	</widget>
	<ePixmap position="20,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/red.png" transparent="1" alphatest="on" />
	<ePixmap position="273,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/green.png" transparent="1" alphatest="on" />
	<ePixmap position="526,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/yellow.png" transparent="1" alphatest="on" />
	<ePixmap position="779,740" zPosition="1" size="250,3" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/etools/images/blue.png" transparent="1" alphatest="on" />
	<widget source="key_red" render="Label" position="20,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_green" render="Label" position="273,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_yellow" render="Label" position="526,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
	<widget source="key_blue" render="Label" position="779,695" zPosition="2" size="250,45" valign="center" halign="center" font="Regular;30" transparent="1" />
</screen>"""
######################################################################################
class eupgrade(Screen):
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.skin = SKIN_UPGD
		self.setTitle(_("E-System Upgrade"))
		self.session = session
		self.list_work = []
		self.commamd_line_ipk = []
		self.list_tmp = []
		self.list_reserv = []
		self.iConsole = iConsole()
		self.pngfile = ""
		self.ipk_off = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/ipk_off.png"))
		self.ipk_on = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "Extensions/etools/images/ipk_on.png"))
		self["menu"] = List(self.list_work)
		self.listofpacket()
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "EPGSelectActions", "SetupActions"],
			{
				"cancel": self.cancel,
				"ok": self.mark_list,
				"green": self.sel_install,
				"yellow": self.all_upgrade,
				"red": self.cancel,
				"blue": self.restart_enigma,
			},-1)
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Selective"))
		self["key_yellow"] = StaticText(_("Full"))
		self["key_blue"] = StaticText(_("Restart"))
			
	def mark_list(self):
		line_old = self["menu"].getCurrent()
		if line_old is not None:
			if line_old[-1] != self.ipk_on:
				self.pngfile = self.ipk_on
				self.commamd_line_ipk.append(line_old[0])
				try:
					self.list_tmp.remove(line_old)
				except:
					self.list_tmp = list(self.list_reserv)
					self.list_tmp.remove(line_old)
			else:
				self.pngfile = self.ipk_off
				self.commamd_line_ipk.remove(line_old[0])
				self.list_tmp.append(line_old)
			line_new = (line_old[0], line_old[1], self.pngfile)
			self["menu"].modifyEntry(self["menu"].getIndex(), line_new)
			if self["menu"].getIndex() + 1 >= self["menu"].count():
				self["menu"].setIndex(0)
			else:
				self["menu"].selectNext()
				
	def sel_install(self):
			force_string = '--force-reinstall'
			if len(self.commamd_line_ipk) >= 1:
				self.session.open(Console, title = _("Upgrade packets"), cmdlist = ["opkg install %s %s" % (force_string, ' '.join(self.commamd_line_ipk))])
				self.commamd_line_ipk = []
			try:
				self.list_work = list(self.list_tmp)
				self["menu"].updateList(self.list_work)
			except:
				pass
				
	def all_upgrade(self):
		self.session.open(Console, title = _("Upgrade packets"), cmdlist = ["opkg upgrade"])
		self.list_work = []
		self["menu"].updateList(self.list_work)
		
	def listofpacket(self):
		self.iConsole.ePopen("opkg list-upgradable", self.stdout_find)
		
	def stdout_find(self, result, retval, extra_args):
		if len(result) == 0:
			self.setTitle(_("E-System Upgrade - Packages for upgrade no avaible"))
		for line in result.splitlines(True):
			try:
				self.list_work.append((line.split()[0], line.split()[2], self.ipk_off))	
			except:
				pass
			
		self.list_work.sort()
		self.list_tmp = list(self.list_work)
		self.list_reserv = list(self.list_work)
		self["menu"].setList(self.list_work)
		
	def restart_enigma(self):
		self.session.open(TryQuitMainloop, 3)
	
	def cancel(self):
		self.close()
######################################################################################
def menu(menuid, **kwargs):
	if menuid == "mainmenu":
		return [(_("E-Tools"), mainmenu, _("etools_"), 47)]
	return []

def edownloader(session, **kwargs):
	session.open(eDownloadFeed)

def eremover(session, **kwargs):
	session.open(eRemoveIPK)

def efeedinst(session, **kwargs):
	session.open(InstallFeed)
	
def camrestart(session, **kwargs):
	session.open(qemurestart)
	
def hdmiinf(session, **kwargs):
	session.open(switch2hdmiin)
	
def audiodmix(session, **kwargs):
	session.open(ac3dwnmix)
	
def switchconfig(session, **kwargs):
	session.open(qemuswitchconfig)
	
def ecrontab(session, **kwargs):
	session.open(CrontabMan)
	
def script_runner(session, **kwargs):
	session.open(EScriptScreen2)
	
def crview(session, **kwargs):
	session.open(eCrashLogScreen)
	
def bouquets_reload(session, **kwargs):
	session.open(BouquetsReload)
	
def setupipk(session, **kwargs):
	session.open(einstaller)
	
def camman(session, **kwargs):
	session.open(emuSelelection)
	
def mainmenu(session, **kwargs):
	session.open(etoolsmainmenu)
	
def sysup(session, **kwargs):
	session.open(eupgrade)

def main(session, **kwargs):
	session.open(etoolsConfigExtentions2)

def mainswap(session, **kwargs):
	session.open(ESwapScreen2)
	
def pluginbrext(session, **kwargs):
	session.open(PluginBrowser)

def sessionstart(reason, session=None, **kwargs):
	if reason == 0:
		pQdm.gotSession(session)
		
pQdm = EHotKey()
######################################################################################
def Plugins(**kwargs):
	if config.plugins.etools.showplugin.value == 'Config':
		list = [PluginDescriptor(name=_("2boom's E-Tools"), description=_("enigma2 toolbox"), where = [PluginDescriptor.WHERE_PLUGINMENU], icon="etools.png", fnc=main)]
	else:
		list = [PluginDescriptor(name=_("2boom's E-Tools"), description=_("enigma2 toolbox"), where = [PluginDescriptor.WHERE_PLUGINMENU], icon="etools.png", fnc=mainmenu)]
	if config.plugins.etools.showemmenu.value:
		list.append(PluginDescriptor(name=_("E-Tools Menu"), description=_("enigma2 toolbox"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=mainmenu))
	if config.plugins.etools.showeconfig.value:
		list.append(PluginDescriptor(name=_("E-Tools Config"), description=_("enigma2 toolbox"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=main))
	if config.plugins.etools.sysupext.value:
		list.append(PluginDescriptor(name=_("E-System Upgrade"), description=_("enigma2 toolbox"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=sysup))
	if config.plugins.etools.showmain.value:
		list.append(PluginDescriptor(name=_("E-Tools"), description=_("E-Tools"), where = [PluginDescriptor.WHERE_MENU], fnc=menu))	
	if config.plugins.etools.crash.value:
		list.append(PluginDescriptor(name=_("E-Crash viewer (%s)" % config.plugins.etools.crashpath.value.rstrip('/')), description=_("E-Crash viewer"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=crview))
	if config.plugins.etools.showscript.value:
		list.append(PluginDescriptor(name=_("E-Script executer (%s)" % config.plugins.etools.scriptpath.value.rstrip('/')), description=_("E-Tools script executer"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=script_runner))
	if config.plugins.etools.reloadbouquets.value:
		list.append(PluginDescriptor(name=_("E-Reload (%s)" % USERBQ[int(config.plugins.etools.reloads.value)] ), description=_("E-Tools: lamedb/Userbouquets"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=bouquets_reload))
	if config.plugins.etools.showsetupipk.value:
		list.append(PluginDescriptor(name=_("E-Installer (%s mode)" % config.plugins.etools.multifilemode.value), description=_("E-Tools IPK Installer"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=setupipk))
	if config.plugins.etools.ext.value:
		list.append(PluginDescriptor(name=_("E-Softcam manager (%s)" % config.plugins.etools.activeemu.value.split()[0]), description=_("E-Tools SoftCam manager"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=camman))
	if config.plugins.etools.extrestart.value:
		list.append(PluginDescriptor(name=_("E-Softcam restart"), description=_("E-Tools SoftCam restart"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=camrestart))
	if config.plugins.etools.extswitch.value:
		list.append(PluginDescriptor(name=_("E-Softcam config switch (%s)" % config.plugins.etools.activeemu.value.split()[0]), description=_("E-Tools config switch"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=switchconfig))
	if config.plugins.etools.hdmiin.value:
		list.append(PluginDescriptor(name=_("E-HDMI-IN - %s" % config.plugins.etools.hdmiinonoff.value), description=_("E-HDMI-IN On/Off"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=hdmiinf))
	if config.plugins.etools.ac3dmixext.value:
		list.append(PluginDescriptor(name=_("E-AC3,DTS downmix - %s" % config.plugins.etools.ac3state.value), description=_("E-AC3,DTS downmix On/Off"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=audiodmix))
	if config.plugins.etools.pluginbrext.value:
		list.append(PluginDescriptor(name=_("Plugin Browser"), description=_("plugin browser"), where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=pluginbrext))
	list.append(PluginDescriptor(where = [PluginDescriptor.WHERE_AUTOSTART, PluginDescriptor.WHERE_SESSIONSTART],fnc = sessionstart))
	return list
	
