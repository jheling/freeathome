# freeathome

Free@Home component for Home Assistant

This is a component for Free @ Home from Busch-Jaeger.
Lights, scenes, covers, binary sensors, climate devices and the sensors of the weather station wil show up in Home Assistant. 

## Installation

Place the files in the custom_components directory. This should be in the same directory as the configuration.yaml.
Then you can do a restart of Home Assistant.

With Home Assistant version 0.88 the way sources should be placed in the custom_components directory has changed. 
This version won't work on earlier versions.

Free@home now appears as an integration in Home Assistant. 

## Configuration

The sysap will be autodetected through zeroconf. Then you only have to fill in a username and password.

If the sysap is not autodetected, you can add the integegration. Then you have to add a host, username and password.

The configuration.yaml can still be used, then u have to add the following lines:
``` 
freeathome:
  host: <ip adress of the sysapserver> or SysAP.local  
  username: <Username in free@home>    
  password: <Password in free@home>    
  use_room_names: <This is optional, if True then combine the device names with the rooms>
```  

## Debugging

If one of your devices does not work, feel free to open an issue. Please provide some debugging information about your setup.

In order to add new devices, please also send a copy of your free@home device XML configuration. You may obtain one like this:

* Go to _Developer Tools_ -> _Services_
* Enter _Service_: `freeathome.dump`
* Leave _Service data_ empty
* Hit _Call Service_

Then look in your Home Assistant configuration folder for a file called `freeathome_dump_<ip>.xml` and attach it to an issue (e.g. by using https://paste.ubuntu.com/).

## Credits

Thanks to Foti for testing the cover device!
Thanks to Lasse Magnussen for the climate device!
Thanks to Nadir for testing the weather station
