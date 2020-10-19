# # TODO: Use FahSensor for movement detector lux sensor
# # TODO: Use FahSensor for weather station sensors
# class FahSensor(FahDevice):
#     """ Free@Home sensor object """
#     state = None     
#     output_device = None    
# 
#     def __init__(self, client, device_info, serialnumber, channel_id, name, sensor_type, state, output_device):
#         FahDevice.__init__(self, client, device_info, serialnumber, channel_id, name)
#         self.type = sensor_type
#         self.state = state        
#         self.output_device = output_device
