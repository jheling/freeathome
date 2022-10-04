"""Constants."""
FUNCTION_IDS_BINARY_SENSOR = [
        0x0000, # Control element
        0x0001, # Dimming sensor
        # 0x0002: Blind sensor is ignored, since it does not have an on/off state (odp0000)
        0x0003, # Blind sensor
        0x0004, # Stairwell light sensor
        0x0005, # Force On/Off sensor
        0x0006, # Scene sensor
        0x000C, # Wind alarm
        0x000D, # Frost alarm
        0x000E, # Rain alarm
        0x000F, # Window sensor
        0x0011, # Movement detector sensor
        0x0028, # Force-position blind
        0x002A, # Switchover heating/cooling
        0x0071, # Timer program switch sensor
        0x1008, # FID_SWITCH_SENSOR_PUSHBUTTON_TYPE0
        0x1009, # FID_SWITCH_SENSOR_PUSHBUTTON_TYPE1
        0x100A, # FID_SWITCH_SENSOR_PUSHBUTTON_TYPE2
        0x100B, # FID_SWITCH_SENSOR_PUSHBUTTON_TYPE3
        0x1018, # FID_DIMMING_SENSOR_PUSHBUTTON_TYPE0
        0x1019, # FID_DIMMING_SENSOR_PUSHBUTTON_TYPE1
        0x101A, # FID_DIMMING_SENSOR_PUSHBUTTON_TYPE2
        0x101B, # FID_DIMMING_SENSOR_PUSHBUTTON_TYPE3
        0x1028, # FID_STAIRCASE_LIGHT_SENSOR_PUSHBUTTON_TYPE0
        0x1029, # FID_STAIRCASE_LIGHT_SENSOR_PUSHBUTTON_TYPE1
        0x102A, # FID_STAIRCASE_LIGHT_SENSOR_PUSHBUTTON_TYPE2
        0x102B, # FID_STAIRCASE_LIGHT_SENSOR_PUSHBUTTON_TYPE3
        0x1040, # FID_BLIND_SENSOR_ROCKER_TYPE0
        0x1041, # FID_BLIND_SENSOR_ROCKER_TYPE1
        0x1042, # FID_BLIND_SENSOR_ROCKER_TYPE2
        0x1058, # FID_FORCE_ON_OFF_SENSOR_PUSHBUTTON_TYPE0
        0x1059, # FID_FORCE_ON_OFF_SENSOR_PUSHBUTTON_TYPE1
        0x105A, # FID_FORCE_ON_OFF_SENSOR_PUSHBUTTON_TYPE2
        0x105B, # FID_FORCE_ON_OFF_SENSOR_PUSHBUTTON_TYPE3
        

        ]

FUNCTION_IDS_SWITCHING_ACTUATOR = [
        0x0007, # Switch actuator
        0x0045, # Trigger
        ]

FUNCTION_IDS_DIMMING_ACTUATOR = [
        0x0012, # Dimmer
        0x1810, # FID_DIMMING_ACTUATOR_TYPE0
        0x1819, # FID_DIMMING_ACTUATOR_TYPE9
        ]

FUNCTION_IDS_ROOM_TEMPERATURE_CONTROLLER = [
        0x000A, # Room temperature controller with fan speed
        0x000B, # Room temperature controller extension unit
        0x0023, # Room temperature controller
        0x003E, # Room temperature controller with fan speed wireless?
        0x003F, # Room temperature controller with fan speed wireless?
        ]

FUNCTION_IDS_BLIND_ACTUATOR = [
        0x002C, # Cover (undocumented)
        0x0061, # Roller blind actuator
        0x0062, # Attic window actuator
        0x0063, # Awning actuator
        0x1820, # FID_BLINDS_ACTUATOR_TYPE0
        0x1821, # FID_BLINDS_ACTUATOR_TYPE1
        0x1822, # FID_BLINDS_ACTUATOR_TYPE2
        0x1823, # FID_BLINDS_ACTUATOR_TYPE3
        0x1825, # FID_BLINDS_ACTUATOR_TYPE5
        ]

FUNCTION_IDS_SHUTTER_ACTUATOR = [
        0x0009, # Shutter actuator
        ]

FUNCTION_IDS_SCENE = [
        0x4000, # Light group
        0x4800, # Custom scene
        0x4801, # Panic scene
        0x4802, # All lights off
        0x4803, # All blinds open
        0x4804, # All blinds closed
        ]

FUNCTION_IDS_MOVEMENT_DETECTOR = [
        0x0011, # Movement detector sensor
        0x1090, # FID_MOVEMENT_DETECTOR_TYPE0
        0x1091, # FID_MOVEMENT_DETECTOR_SLAVE_TYPE0
        0x1092, # FID_MOVEMENT_DETECTOR_TYPE2
        0x1093, # FID_MOVEMENT_DETECTOR_TYPE3
        0x1094, # FID_MOVEMENT_DETECTOR_TYPE4
        0x1095, # FID_MOVEMENT_DETECTOR_SLAVE_TYPE3
        0x1096, # FID_MOVEMENT_DETECTOR_SLAVE_TYPE4
        ]

FUNCTION_IDS_DOOR_OPENER = [
        0x001A, # Door opener actuator
        ]

FUNCTION_IDS_WEATHER_STATION = [
        0x0041, # Brightness sensor
        0x0042, # Rain sensor
        0x0043, # Temperature sensor
        0x0044, # Wind sensor
        ]

NAME_IDS_TO_BINARY_SENSOR_SUFFIX = {
        0x000A: '',   # 1-way
        0x0043: ' L',  # 2-way left
        0x0044: ' R',  # 2-way right
        0x0045: ' LT', # 2-way left, top
        0x0046: ' LB', # 2-way right, bottom
        0x0047: ' RT', # 2-way right, top
        0x0048: ' RB', # 2-way right, bottom
        0x0066: ' T',  # 1-way, top
        0x0067: ' B',
        }

### Pairing IDs

# Switch actuator
PID_SWITCH_ON_OFF = 0x0001
PID_ABSOLUTE_SET_VALUE = 0x0011
PID_INFO_ON_OFF = 0x0100
PID_INFO_ACTUAL_DIMMING_VALUE = 0x0110

# Cover
PID_MOVE_UP_DOWN = 0x0020
PID_ADJUST_UP_DOWN = 0x0021
PID_SET_ABSOLUTE_POSITION_BLINDS = 0x0023
PID_SET_ABSOLUTE_POSITION_SLATS = 0x0024
PID_FORCE_POSITION_BLIND = 0x0028
PID_INFO_MOVE_UP_DOWN = 0x0120
PID_CURRENT_ABSOLUTE_POSITION_BLINDS_PERCENTAGE = 0x0121
PID_CURRENT_ABSOLUTE_POSITION_SLATS_PERCENTAGE = 0x0122
PID_FORCE_POSITION_INFO = 0x0101

# Thermostat
PID_ECO_MODE_ON_OFF_REQUEST = 0x003A
PID_CONTROLLER_ON_OFF_REQUEST = 0x0042
PID_ABSOLUTE_SETPOINT_TEMPERATURE = 0x0140
PID_SET_VALUE_TEMPERATURE = 0x0033
PID_CONTROLLER_ON_OFF = 0x0038
PID_STATUS_INDICATION = 0x0036
PID_MEASURED_TEMPERATURE = 0x0130
PID_HEATING_DEMAND = 0x014D

# Thermostat parameters
PARAM_TEMPERATURE_CORRECTION = 0x001B

# Movement detector
PID_MOVEMENT_UNDER_CONSIDERATION_OF_BRIGHTNESS = 0x0006
PID_PRESENCE = 0x0007
PID_MEASURED_BRIGHTNESS = 0x0403

# Scenes
PID_SCENE_CONTROL = 0x0004

# Binary sensor
# PID_SWITCH_ON_OFF = 0x0001 defined above
PID_TIMED_START_STOP = 0x0002
PID_FORCE_POSITION = 0x0003
# PID_SCENE_CONTROL = 0x0004 defined above
PID_RELATIVE_SET_VALUE = 0x0010
# PID_MOVE_UP_DOWN = 0x0020 defined above
# PID_ADJUST_UP_DOWN = 0x0021 defined above
PID_WIND_ALARM = 0x0025
PID_FROST_ALARM = 0x0026
PID_RAIN_ALARM = 0x0027
# PID_FORCE_POSITION_BLIND = 0x0028 defined above
PID_WINDOW_DOOR = 0x0035
PID_SWITCHOVER_HEATING_COOLING = 0x0135

# Lock
# PID_TIMED_START_STOP = 0x0002 defined above
# PID_INFO_ON_OFF = 0x0100 defined above

# Weather station
PID_OUTDOOR_TEMPERATURE = 0x0400
# PID_MEASURED_BRIGHTNESS = 0x0403 defined above
PID_WIND_SPEED = 0x0404
PID_RAIN_DETECTION = 0x0405
