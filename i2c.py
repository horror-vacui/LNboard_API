import logging
logger = logging.getLogger(__name__)

class I2C_device(object):  # object is needed to be compatible with Florian's python2.7 code.
    """ 
        Paramters: 
            addr:   I2C address. The 7bit address is given.
    """

    def __init__(self, gateway, addr, name="", emulate=True):
        assert addr < pow(2,8), "Address should be only 7 bit. Specified addres: %s" % hex(addr)
        self.addr = addr # We store the 8bit version, i.e. the Write address.
        self.name = name  # optional. Not sure I will use this
        self.gateway = gateway # I2C gateway, i.e. Buspirate instance
        self.emulate = emulate
        logger.debug("I2C device instance created with name= " + name + ";   and I2C address= %s (%s)" % (hex(addr), hex(addr << 1))  )
        

    def get_bit(reg,n_bit):
        """ returns the value of the nth bit of reg. """
        return reg >> n_bit & 1

    def int_to_bytelist(val):
        l_b = []
        while val > 0:
            l_b.insert(0, val & 0xff)
            val = val >> 8
        return l_b 

    def int_to_n_byte(self, val, n):
        l_b = []
        while n > 0:
            l_b.insert(0, val & 0xff)
            val = val >> 8
            n -=1
        return l_b 

    def write(self, reg, data, ndata):
        """ Writes the ndata (int) data bytes of data (int) into regiter reg of the device. Error is raised if data is longer than ndata. 
        
        If the chip has only one register and therefore it has no register address, set data=0 and ndata=0, 
        and give the intended register value to the "reg" argument. """
        if self.emulate: 
            pass
        else:
            l_tx = [(self.addr << 1), reg ]
            l_data = []
            if ndata > 0:
                l_data = self.int_to_n_byte(data, ndata)
                l_tx += l_data
                logger.debug("Write to I2C_ADDR=%s(%s); REG=%s the DATA=0x.%s;" %(hex(self.addr), hex(self.addr<<1), hex(reg), ".".join(['{:02x}'.format(i) for i in l_data]) ))
            else:
                logger.debug("Write to I2C_ADDR=%s(%s)'s only register; DATA=%s;" %(hex(self.addr), hex(self.addr<<1), hex(reg) ))

            self.gateway.write_then_read( numtx=len(l_tx), numrx=0, txdata=l_tx)

    def read(self, reg, ndata, return_bytes=False):
        """ I2C master stops the read, therefore the number of bytes to be read has to be knonw by the master. 
            :param reg: int; represents the 8bit register address in the I2C chip
            :param ndata: int; number of bytes to read out
            :param return_bytes=False; whether to return python's 'bytes' type
        """
        logger.debug("Read from I2C_ADDR=%s(%s); REG=%s;" %(hex(self.addr), hex((self.addr<<1)+1), hex(reg) ))
        if self.emulate:
            rtn = 0
        else:
            self.gateway.write_then_read(numtx=2, numrx=0, txdata=[(self.addr<<1), reg]) 
            rtn = self.gateway.write_then_read(numtx=1, numrx=ndata, txdata=[(self.addr<<1)+1]) 
            
        if isinstance(rtn, bytes):
            if return_bytes:
                return  rtn
            else:
                return int.from_bytes(rtn, byteorder='big') #bigendian
        else: # return int
            # logging.debug("Return type: %r" % type(rtn))
            return rtn
