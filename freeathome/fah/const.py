"""Constants."""
FUNCTION_IDS_SENSOR_UNIT = [
        0x0000, # Control element
        0x0001, # Dimming sensor
        # 0x0002: Blind sensor is ignored, since it does not have an on/off state (odp0000)
        0x0004, # Stairwell light sensor
        0x0005, # Force On/Off sensor
        0x0006, # Scene sensor
        0x0028, # Force-position blind
        0x0071, # Timer program switch sensor
        ]

FUNCTION_IDS_SWITCHING_ACTUATOR = [
        0x0007, # Switch actuator
        0x0045, # Trigger
        ]

FUNCTION_IDS_DIMMING_ACTUATOR = [
        0x0012, # Dimmer
        ]

FUNCTION_IDS_ROOM_TEMPERATURE_CONTROLLER = [
        0x000A, # Room temperature controller with fan speed
        0x000B, # Room temperature controller extension unit
        0x0023, # Room temperature controller
        ]

FUNCTION_IDS_BLIND_ACTUATOR = [
        0x0009, # Blind actuator
        0x0061, # Roller blind actuator
        0x0062, # Attic window actuator
        0x0063, # Awning actuator
        ]

FUNCTION_IDS_SCENE = [
        0x4000, # Light group
        0x4800, # Custom scene
        0x4801, # Panic scene
        0x4802, # All lights off
        0x4803, # All blinds open
        0x4804, # All blinds closed
        0x4A00, # Timer program switch actuator
        0x4A01, # Alert switch actuator
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
