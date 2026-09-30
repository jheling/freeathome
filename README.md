# freeathome
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

Free@Home component for Home Assistant

This is a component for Free @ Home from Busch-Jaeger.
Lights, light groups, scenes, covers, binary sensors, climate devices and the sensors of the weather station wil show up in Home Assistant. 

## Installation

### Manual
Place the files in the custom_components directory. This should be in the same directory as the configuration.yaml.
Then you can do a restart of Home Assistant.

With Home Assistant version 0.88 the way sources should be placed in the custom_components directory has changed. 
This version won't work on earlier versions.

Free@home now appears as an integration in Home Assistant. 

### HACS
Install this component in HACS by adding it as a custom repository of the type integration.

### Youtube
This is a German tutorial about using Home Assistant for integrating Free@Home and Apple Homekit/Siri. 
It shows how to install Home Assistant and this integration on a Raspberry Pi. 
https://youtu.be/9xfUhRiwK_s

## Configuration

The sysap will be autodetected through zeroconf. Then you only have to fill in a username and password.

If the sysap is not autodetected, you can add the integegration. Then you have to add a host, username and password.

The configuration.yaml can still be used, then u have to add the following lines:
``` 
freeathome:
  host: <ip adress of the sysapserver> or SysAP.local  
  username: <Username in free@home>    
  password: <Password in free@home>    
  use_room_names: <This is optional, if True then combine the device names with the rooms. False by default>
  switch_as_x: <This is optional, if False then switching devices are exposed as lights. True by default>
```

### `switch_as_x` feature

Recently a change has been made to the way switches are exposed in Home Assistant. Before they were all exposed as `light`s but now they are exposed as `switch`es. This would be a breaking change for people who have automations that use the `light.turn_on` service, but it should be working the same as before if you are upgrading from an older version of this custom component. If you want to be sure, you can set the `switch_as_x` option to `False` in your configuration.yaml.

Any new installation of this custom component will have `switch_as_x` set to `True` by default. This means that all switches will be exposed as `switch`es and you'll be able to use the HA [switch_as_x](https://www.home-assistant.io/integrations/switch_as_x/) feature. If you want to expose them as `light`s, you can set `switch_as_x` to `False` in your configuration.yaml.

## Events
Actuators that are exposed in Home Assistant as binary sensors (typically wall switches) fire `freeathome_event` events. Normal switch datapoints continue to emit `pressed`. Dimming sensors additionally emit `dim_start` while a rocker is held and `dim_stop` when it is released.

| Key          | Type   | Example                                      |
|--------------|--------|----------------------------------------------|
| name         | string | Sensor/Dimmaktor 1/1-fach                    |
| serialnumber | string | ABB700CE9999                                 |
| unique_id    | string | ABB700CE9999/ch0000                          |
| state        | bool   | true / false for `pressed` events            |
| command      | string | `pressed`, `dim_start`, or `dim_stop`        |
| direction    | string | `up` or `down` for relative dimming events   |

Relative dimming is decoded from the Free@Home Relative Set Value datapoint (pairing ID `0010`, KNX DPT 3.007). A capture from a Free@Home Sensor/Dimmaktor confirmed the following values:

| Raw value | Command     | Direction |
|-----------|-------------|-----------|
| `9`       | `dim_start` | `up`      |
| `8`       | `dim_stop`  | `up`      |
| `1`       | `dim_start` | `down`    |
| `0`       | `dim_stop`  | `down`    |

The direction is retained on `dim_stop`, because DPT 3.007 carries the direction bit in both stop values. Other valid DPT 3.007 step codes are decoded in the same way.

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

For example, a brightness-increase action can start when the upper rocker is held:
```
trigger:
  - platform: event
    event_type: freeathome_event
    event_data:
      unique_id: ABB700CE9999/ch0000
      command: dim_start
      direction: up
action:
  - service: light.turn_on
    target:
      entity_id: light.nice_lamp
    data:
      brightness_step_pct: 10
      transition: 1
```

Listen for `command: dim_stop` with the same `unique_id` to stop a repeating brightness action when the rocker is released.

### Dimmer status sensor

Each detected two-sided dimming channel also creates an enum sensor on its
existing Free@Home device. A short press is shown briefly before the sensor
returns to `not_pressed`. This makes repeated identical presses visible as
separate Home Assistant state changes. A held action remains visible until the
rocker is released. Single pushbutton channels keep the bus events described
above, but do not get this sensor because they have no upper/lower rocker pair.

| State          | Meaning               |
|----------------|-----------------------|
| `not_pressed`  | No current action     |
| `pressed_up`   | Upper rocker pressed  |
| `pressed_down` | Lower rocker pressed  |
| `held_up`      | Upper rocker held     |
| `held_down`    | Lower rocker held     |

Home Assistant translates these states for display. The `dim_stop` event emitted
on release returns a held status to `not_pressed`.


## Debugging

If one of your devices does not work, feel free to open an issue. Please provide some debugging information about your setup. In order to add new devices, please also send a copy of your free@home device XML configuration as well as some status updates. See below how to obtain both.

### 1. Dumping free@home configuration

* Go to _Developer Tools_ -> _Actions_
* Enter _Service_: `freeathome.dump`
* Leave _Service data_ empty
* Hit _Call Service_

Then look in your Home Assistant configuration folder for a file called `freeathome_dump_<ip>.xml` and attach it to an issue (e.g. by using https://paste.ubuntu.com/).

### 2. Monitoring free@home status updates

* Go to _Developer Tools_ -> _Actions_
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
