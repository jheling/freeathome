

class MessageReader():
    def __init__(self, data):
        self.data = data
        self.offset = 0

    def readUint8(self):
        if self.offset + 1 > len(self.data):
            raise Exception('Insufficient data for reading')    

        self.offset += 1 
        return self.data[self.offset - 1]

    def readUint16(self):
        if self.offset + 2 > len(self.data):
            raise Exception('Insufficient data for reading')

        x = int.from_bytes(self.data[self.offset:self.offset + 2],"little")
        self.offset += 2
        return x        

    def readUint32(self):

        if self.offset + 4 > len(self.data):
            raise Exception('Insufficient data for reading')    
 
        x = int.from_bytes(self.data[self.offset:self.offset + 4],"little")
        self.offset += 4
        return x

    def readUint64(self):
        if self.offset + 8 > len(self.data):
            raise Exception('Insufficient data for reading')

        g = self.readUint32()
        f = self.readUint32()
        if f != 0:
            raise Exception('Cannot read 64 bit value: upper 32 bits have value != 0')    

        return g

    def readUint32BE(self):
        if self.offset + 4 > len(self.data):
            raise Exception('Insufficient data for reading')

        return (self.readUint8() << 24) | (self.readUint8() << 16) | (self.readUint8() << 8) | self.readUint8()
    
    def readString(self):  
        i = self.readUint32()
        if self.offset + i > len(self.data):
            raise Exception('Insufficient data for reading')

        print('i:',i)

        text = self.data[self.offset: self.offset + i ].decode('utf-8')
        self.offset += i
        return text

    def readBlob(self, amount):
        if self.offset + amount > len(self.data):
            raise Exception('Insufficient data for reading')

        blob = self.data[self.offset: self.offset + amount ]
        self.offset += amount
        return blob
    
    def getRemainingData(self):
        return self.data[self.offset:]
    
