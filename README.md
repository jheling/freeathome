# freeathome
Free@Home component for Home Assistant

This is a first start for a component for Free @ Home from Busch-Jaeger.
Now lights, scenes, covers, binary sensors and climate devices wil show up in Home Assistant. 

Place the files in the custom_components directory. This should be in the same directory as the configuration.yaml.

Put the following in configuration.yaml:

freeathome:

    host: <ip adress of the sysapserver> 

    username: <Username in free@home>
    
    password: <Password in free@home>
    
    use_room_names: <This is optional, if True then combine the device names with the rooms>
  
Thanks to Foti for testing the cover device!
Thanks to Lasse Magnussen for the climate device!

With Home Assistant version 0.88 the way sources should be placed in the custom_components directory has changed. 
This version won't work on earlier versions.
