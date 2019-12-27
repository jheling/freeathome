class MessageWriter:

    def __init__(self):
        self.data = []

    def writeUint8(self, value):
        if value > 255:
            raise Exception('Refusing attempt to write ', value_bytes, ', exceeding the value of a uint.')
        item = {'type': 'uint8', 'value': value}
        self.data.append(item)

    def writeUint32(self, value):
        item = {'type': 'uint32', 'value': value}
        self.data.append(item)

    def writeString(self, value):
        value_bytes = value.encode()
        if len(value_bytes) > 1024 * 1024 * 10:
            raise Exception('Refusing attempt to write ', len(value_bytes), ' bytes of data, exceeding valid range.')

        item = {'type': 'string', 'value': value_bytes}
        self.data.append(item)

    def writeBlob(self, value):
        if len(value) > 1024 * 1024 * 10:
            raise Exception('Refusing attempt to write ', len(value), ' bytes of data, exceeding valid range.')
        item = {'type': 'blob', 'value': value}
        self.data.append(item)

    def toUint8Array(self):
        length = 0

        # Iterate the data
        for d in self.data:
            if d['type'] == 'uint8':
                length += 1

            if d['type'] == 'uint32':
                length += 4

            if d['type'] == 'string':
                length += 4 + len(d['value'])

            if d['type'] == 'blob':
                length += len(d['value'])

        pos = 0
        array_bytes = bytearray()

        for d in self.data:
            if d['type'] == 'uint8':
                x = d['value'].to_bytes(1, byteorder='little')
                print(type(x))
                array_bytes = array_bytes + x
                pos += 1

            if d['type'] == 'uint32':
                array_bytes = array_bytes + d['value'].to_bytes(4, byteorder='little')
                pos += 4

            if d['type'] == 'string':
                array_bytes = array_bytes + len(d['value']).to_bytes(4, byteorder='little')
                array_bytes = array_bytes + d['value']
                pos += 4 + len(d['value'])

            if d['type'] == 'blob':
                array_bytes = array_bytes + d['value']
                pos += len(d['value'])

        return array_bytes
