# NET Guard  
  
Mmonitors the local network. Shows a list with all connected devices and warns with an audible alarm when it detects a new or untrusted device.  
  
## Hotkeys  
  
* Control+Alt+Shift+G Restores the application window if it is minimized.  
* Escape minimize the window to the tray.  
* Enter on a device in the list displays the properties dialog for that device. In this dialog you can set a name for the device and assign it a trust level (red/yellow/green).  
* Control+C Copies to the clipboard the MAC address of the device selected in the list.  
* F5 while it is waiting for the next scheduled scan, it starts the scan immediately.  
  
## Settings  
  
In the settings dialog you can set the following parameters:  
  
* The number of simultaneous threads during the scan.  
* The waiting time between one scan and the next.  
* Turn sound effects on or off.  
  
Changes to the number of threads and the wait time will be applied on the next scan cycle. Turning off sound effects does not affect the alarm, only to the sounds at the window.  
  
## License  
  
  Copiritht (C) Javi Dominguez 2023  
  NET Guard is free software. Copying, distribution and modification is permitted under the license
[GNU General Public License GPL 3.0.](https://www.gnu.org/licenses/gpl-3.0.html)  
It uses [getmac module](https://github.com/GhostofGoes/getmac) by Christopher Goes under [MIT license](https://github.com/GhostofGoes/getmac/blob/main/LICENSE).  
Other resources such as audio clips and icons are used under a Creative Commons license.  
