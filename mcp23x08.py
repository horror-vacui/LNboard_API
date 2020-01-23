from i2c import I2C_device
import logging
logger = logging.getLogger(__name__)

class mcp23008(I2C_device):
    """ 8-Bit I/O Expander with Serial Interface """
    
    R_IODIR     = 0x00
    R_IPOL      = 0x01
    R_GPINTEN   = 0x02
    R_DEFVAL    = 0x03
    R_INTCON    = 0x04
    R_IOCON     = 0x05
    R_GPPU      = 0x06
    R_INTF      = 0x07
    R_INTCAP    = 0x08
    R_GPIO      = 0x09
    R_OLAT      = 0x0a

    def __init__(self, addr2, addr1, addr0, 
                gateway,
                name   = "MCP23008T I/O Expander",
                n_bits = 8
                ):  
        assert addr0 in [0,1]
        assert addr1 in [0,1]
        assert addr2 in [0,1]

        address    = (0b0100<<3)  +  (addr2<<2)  +  (addr1<<1)  +  addr0 
        super().__init__(addr=address, gateway=gateway, name=name)
        self.n_bits     = n_bits

    def set_io_dir(self, value):
        """ Set the IO Direction register. Input=1, Output=0. """
        self.write( reg=self.R_IODIR, data = (value & 0xff), ndata=1 )

    def get_io_dir(self):
        """ Read the IO Direction register. """
        self.read( reg=self.R_IODIR, ndata=1 )

    def get_olat(self):
        """ Read the Output Latch Register (OLAT) register. """
        self.read( reg=self.R_OLAT, ndata=1 )

    def get_gpio(self):
        """ Returns the GPIO register"""
        return self.read(reg=self.R_GPIO, ndata=1) 

    def get_gpio_bit(self, idx_bit):
        """ Returns the status of the idx_bit-th GPIO pin
            
            Paramters
            ---------
            idx_bit :   int
                        the index of the bit whose value to return. [0,7]

            Returns
            -------
            int
                        The bit value. 0 or 1.
            """
        return (self.read(reg=self.R_GPIO, ndata=1) >> idx_bit) & 1

    def set_gpio(self, value=1):
        """ Set the value of the GPIO register """
        assert 0<=value<=0xff, f"The specified register value - {hex(value)} - is out of range: (0x00, 0xff)"
        # add logging here, with warning if value is more than 0xff
        self.write( reg = self.R_GPIO, data = (value & 0xff), ndata=1 )

    def set_gpio_bit(self, idx_bit, value=1):
        """ Setthe value of the idx_bit-th GPIO pin """
        self.write( reg = self.R_GPIO, data = (self.get_gpio() & ~(1<<idx_bit) | ((value & 1)<<idx_bit)), ndata=1 )


