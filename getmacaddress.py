#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Console application to get the MAC address of the computer connected to the given IP.

get_mac_address function causes errors when run in a GUI application. It is preferable to compile this file for console and run it as a subprocess instead of calling it directly from the scanner module.

getmac module is copyrighted by Christopher Goes. It is used under MIT license as part of NET Guard
https://github.com/GhostofGoes/getmac
https://github.com/GhostofGoes/getmac/blob/main/LICENSE
https://github.com/javidominguez/netGuard

Copyright (C) 2023 Javi Dominguez 
This file is covered by the GNU General Public License.
See the file COPYING for more details.
"""

import sys
from getmac import get_mac_address

def getmac(IP):
    return get_mac_address(ip=IP)

if __name__ == "__main__":
    mac = getmac(sys.argv[1])
    if mac: print(mac)