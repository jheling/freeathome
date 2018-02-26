# freeathome
Free@Home component for Home Assistant

This is a first start for a component for Free @ Home from Busch-Jaeger.
In this version only the lights wil show up in Home Assistant. All the other components are not coded yet.

Place the files in the custom_components directory. This should be in the same directory as the configuration.yaml.

Put the following in configuration.yaml:

freeathome:
  host: <ip adress of the sysapserver> 
  username: <Username in free@home>
  password: <Password in free@home>
  use_room_names: <This is optional, if True then combine the device names with the rooms>
  
