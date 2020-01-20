from i2c import I2C_device
import logging
logger = logging.getLogger(__name__)

class pca9542a(I2C_device):
    """ Class for PCA9542A type I2C multiplexer 
            The slave address is hardwired.
            Valid channel values are 0 or 1. These indicate the active output subbus.
            Enable is 1 or 0.

            Sending to the device any byte after the slave address will write its control register.
        """

    B1     = 1
    B0     = 0
    ENABLE = 2
    ADDR_MSB = 0b1110 << 3

    def __init__(self, gateway, a2a1a0=0b000, channel=0, enable=1, name="PCA9542A: I2C multiplexer"):  
        super().__init__(addr=self.ADDR_MSB + a2a1a0, name=name, gateway=gateway)
        # I2C_device.__init__(self,addr,name=name)
        self.channel    = channel
        self.enable     = enable
        self.subchannel = None
        self.__call__   = self.set_channel

    def read(self, return_bytes=False):
        """ redefine I2C.read() because we have no register address, and we 
        return always 1 byte. """
        rtn = self.gateway.write_then_read(numtx=1,numrx=1,txdata=[(self.addr<<1)+1])
        if return_bytes:
            return rtn
        else:
            return int.from_bytes(rtn, byteorder='big') # bigendian

    def set_channel(self, channel):
        """ Set the active channel. Set channel value to 'None' to disable both busses. """
        assert channel in [0,1,None]
        if channel == None: # disable both subbuses
            self.write(reg=0, data=0, ndata=0)
        if channel in [0,1]:
            assert self.enable in [0,1]
            # self.write(reg = (self.enable << 2) + channel, data=0, ndata=0)
            logger.debug(f"I2C_subchannel={channel}")
            self.gateway.command(self.addr, (self.enable << 2) + channel)
            self.subchannel == channel

    def get_channel(self):
        """ reads the control register. """
        tmp = self.read()
        # if (self.get_bit(self.read(), ENABLE) == 1) & (self.get_bit(tmp, B1) == 0): # enabled
        if ((tmp & 0x06) == 0b100 ): # B2=ENABLE==1 and B1==0 
            return tmp & 0x01 # B0, i.e. the LSB carries the channel information
        else:
            return None

