from i2c import I2C_device
import logging


class mcp466x(I2C_device):
    """ 7/8-Bit Single/Dual I 2 C Digital POT with Nonvolatile Memory 
   

        Device types: 
          0th bit: {1:"potentiometer", 2: "rheostat"}
          1th bit: {3 & 4: 7bit;   5 & 6: 8 bit potentiometer}
          1th bit: {3 & 5: RAM ;   4 & 6: EEPROM}
          2th bit: {5: 1 unit in the package, 6: 2 unit in the package
          

        Tip:
        - Use 5.5V supply if possible for better INL and RNL (=precision and accuracy).
    """
    # TODO: write a regex in the init method: it will set n_bits, and n_channels, generate name
    # plus it would do extra checking

    L_RAB_OPTIONS = (5e3,10e3,50e3,100e3)   # Ohm
    L_CHANNEL = (0,1)

    # Command byte: 4bit reg address + 2 bit command + 2 bit data MSB
    R_WIPER    = 0 << 4   # Volatile Wiper
    R_VWIPER0  = 0 << 4   # Volatile Wiper
    R_VWIPER1  = 1 << 4
    R_NVWIPER0 = 2 << 4   # Non-volatile Wiper
    R_NVWIPER1 = 3 << 4
    R_TCON     = 4 << 4   #
    R_STATUS   = 5 << 4
    # The devices also contains 10 byte EEPROM: 0x06-0x0f

    # Commands:
    C_WRITE = 0b00 << 2
    C_INC   = 0b01 << 2 # increment regsiter
    C_DEC   = 0b10 << 2 # decrement
    C_READ  = 0b11 << 2 

    D_FIX_ADDRESS = 0b0101110 # last few bits are overriden by the address pins
    D_N_ADDR_PIN  = {
            "MCP45x1":1,
            "MCP45x2":2,
            "MCP46x1":3,
            "MCP46x2":2,
            } # A0 is used for High-Voltage commands and the value is latched at POR

    # Addresses incl W bit:
    #  channel0      | 5k   | 100k |
    # -----------------------------|
    # current sink   | 0x58 | 0x5a |
    # current source | 0x5c | 0x5e |
    #
    #  channel1      | 50k  |
    # -----------------------
    # LDO resistor   | 0x58 |
    #
    # rheos = { 'sink':   {5e3:0x58, 100e3:0x5a },
    #         'source': {5e3:0x5c, 100e3:0x5e },
    #         'ldo':    0x58
    #         }

    def __init__(self, addr1, addr0, 
                gateway,
                fullscale=5e3, 
                n_bits=8, 
                dev_type="MCP4662",
                name="MCP4662 Rheostat"
                ):  
        assert fullscale in self.L_RAB_OPTIONS, "Invalid RAB resistor option. The fullscale resistance values are: " + ", ".join([str(i) for i in self.L_RAB_OPTIONS])
        assert n_bits in [7, 8], "Invalid number of bits. Valid bit numbers are 7 and 8."
        assert addr0 in [0,1]
        assert addr1 in [0,1]


        address    = (0b01011 << 2) + (addr1<<1) + addr0 
        # logging.debug("addr1=%r\taddr0=%r\t\taddress=%r" % (addr1, addr0, address))
        super().__init__(addr=address, gateway=gateway, name=name)
        self.fullscale  = fullscale
        self.n_bits     = n_bits
        self.res_step   = self.fullscale/(2**self.n_bits) # fullscale is in kOhms
        self.Rw_typ     = 75 # Ohm; wiper resistance

    def res2code(self, res):
        """ Calculate the code required for a given resistance """
        assert 0 < res <= self.fullscale, "The desired resistor value, %r, is out of range. The valid range is between 0 and %r" % (res, self.fullscale)
        return round( (res-self.Rw_typ)/self.res_step)

    def code2res(self, code):
        """ Calculate the resistance corresponding to a given code """
        assert 0 <= code < (1 << self.n_bits), "code is out of range"
        return self.res_step*code + self.Rw_typ

    def set_wiper(self, code, channel=0):
        """ Write the intended code to the rheostat register. """
        assert channel in self.L_CHANNEL, "Invalid channel number. Valid channel numbers are " + ", ".join([str(i) for i in self.L_CHANNEL])
        assert 0<= code <= (1 << self.n_bits), "code has to be n_bits+1 long"  # Maybe put it into a "try:" and cut the higher bits
        
        # The command byte includes the 2 MSBs of the data as well!
        code_MSBs = code >> 8
        code_LSBs = code & 0x00ff
        self.write(   
                reg   = ( (self.R_WIPER + channel + self.C_WRITE)<<8 ) + code_MSBs,
                data  = code_LSBs,
                ndata = 1 
                )
    
    def get_wiper(self, channel=0):
        """ Read the wiper register. Since there are 9 data bits, it will read two bytes. """
        return self.read(reg=(self.R_WIPER+channel + self.C_READ), ndata=2)

    def get_register(self, reg):
        """ Read given register. Returns 2 bytes """
        return self.read(reg,2)

    def get_last_register(self):
        """ See Fig 7-4 in the datasheet. Read from Last Memory Address Accessed. Writes one and returns two bytes. i
            
            Not clear how to implement it with Florian's i2c code: no register is defined.
        """
        return self.read()

    def set_res(self, res, channel=0):
        """ Set the desired resistance value at the wiper """
        assert channel in self.L_CHANNEL
        self.set_wiper(self.res2code(res), channel)

    def get_res(self, channel=0):
        """ Get the actual reistance at the wiper """
        assert channel in self.L_CHANNEL
        return self.code2res( self.get_wiper(channel) )

    def inc_wiper(self, channel=0):
        """ The Increment Command will only
            function on the volatile wiper setting memory locations
            00h and 01h. The Increment Command to Nonvolatile
            addresses will be ignored and will generate a A.

            If multiple Increment Commands are received
            after the value has reached 100h (or 80h), the value will
            not be incremented further.
        """
        assert channel in self.L_CHANNEL
        self.write(
                reg = self.R_WIPER + (channel << 4)  + self.C_INC,
                data = 0,
                ndata = 0
                ) # Again: not clear if it will work with the i2c_tx_handler....

    def dec_wiper(self, channel=0):
        """ Decrement the wiper setting. For more information see the docstring of inc_wiper function. """
        assert channel in self.L_CHANNEL
        self.write(
                reg   = self.R_WIPER + (channel << 4)  + self.C_DEC,
                data  = 0,
                ndata = 0)

