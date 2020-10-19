# TODO: Refactor to use function IDs
# class FahLock(FahDevice):
#     """" Free@home lock controll in 7 inch panel """
#     state = None
# 
#     def __init__(self, client, device_info, serialnumber, channel_id, name, state=False):
#         FahDevice.__init__(self, client, device_info, serialnumber, channel_id, name)
#         self.state = state        
# 
#     async def lock(self):
#         await self.client.set_datapoint(self.serialnumber, self.channel_id, 'idp0000', '0')
#     
#     async def unlock(self):
#         await self.client.set_datapoint(self.serialnumber, self.channel_id, 'idp0000', '1')
