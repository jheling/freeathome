# freeathome
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

Free@Home component for Home Assistant

This is a component for Free @ Home from Busch-Jaeger.
Lights, scenes, covers, binary sensors, climate devices and the sensors of the weather station wil show up in Home Assistant. 

## Installation

### Manual
Place the files in the custom_components directory. This should be in the same directory as the configuration.yaml.
Then you can do a restart of Home Assistant.

With Home Assistant version 0.88 the way sources should be placed in the custom_components directory has changed. 
This version won't work on earlier versions.

Free@home now appears as an integration in Home Assistant. 

### HACS
Install this component in HACS by adding it as a custom repository of the type integration.

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

## Events
Actuators that are exposed in Home Assistant as binary sensors (typically wall switches) fire an event when pressed. The event type is `freeathome_event` and contains the following actuator's information:

| Key          | Type   | Example                                     |
|--------------|--------|---------------------------------------------|
| name         | string | Actuator Hallway                            |
| serialnumber | string | ABB700CE9999                                |
| unique_id    | string | ABB700CE9999/ch0000                         |
| state        | bool   | true for on / false for off                 |
| command      | string | "pressed" is the only option at this moment |

The event fires regardless of the state of the binary sensory in Home Assistant and Free@Home. Each time the wall switch is pressed, the event fires.

These events can be used in automations. For example to turn on a light every time the actuator's "on" button is pressed:
```
trigger:
  - platform: event
    event_type: freeathome_event
    event_data:
      unique_id: ABB700CE9999/ch0000
      command: pressed
      state: true
action:
  - service: light.turn_on
    target:
      entity_id:
      - light.nice_lamp
```


## Debugging

If one of your devices does not work, feel free to open an issue. Please provide some debugging information about your setup. In order to add new devices, please also send a copy of your free@home device XML configuration as well as some status updates. See below how to obtain both.

### 1. Dumping free@home configuration

* Go to _Developer Tools_ -> _Services_
* Enter _Service_: `freeathome.dump`
* Leave _Service data_ empty
* Hit _Call Service_

Then look in your Home Assistant configuration folder for a file called `freeathome_dump_<ip>.xml` and attach it to an issue (e.g. by using https://paste.ubuntu.com/).

### 2. Monitoring free@home status updates

* Go to _Developer Tools_ -> _Services_
* Enter _Service_: `freeathome.monitor`
* Enter _Service data_: `duration: 5`
* Hit _Call Service_

Now the system will record device updates for the next 5 seconds. Look in your Home Assistant configuration folder for a file called `freeathome_monitor_<ip>.xml` and attach it to your issue (e.g. by using https://paste.ubuntu.com/).

## Credits

Many thanks to Tho85 for building future proof, function based components
Thanks to Foti for testing the cover device!
Thanks to Lasse Magnussen for the climate device!
Thanks to Nadir for testing the weather station
Thanks to jfindlay for making the the pure_pynacl library available: https://github.com/jfindlay/pure_pynacl
Thanks to jeroen84 for the PyNaCl implementation
