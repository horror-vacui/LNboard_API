from i2c import I2C_device
import random, logging
logger = logging.getLogger(__name__)

class max5815(I2C_device):
    """ Class for MAX5815 type DACs.
    The MAX5813/MAX5814/MAX5815 4-channel, low-power,
    8-/10-/12-bit, voltage-output digital-to-analog converters
    (DACs) include output buffers and an internal reference
    that is selectable to be 2.048V, 2.500V, or 4.096V.
    """

    # NOTE: the chip can always receive two bytes of data after a register adress.
    # The not required LSB bits are "don't care"

    ADDR_PRE_TSSOP = 0b001 << 4
    ADDR_TSSOP = {  (1,0):      0b0000,
                    (1,'NC'):   0b0010,
                    (1,0):      0b0011,
                    ('NC',1):   0b1000,
                    ('NC','NC'): 0b1010,
                    ('NC',0):   0b1011,
                    (0,1):      0b1100,
                    (0,'NC'):   0b1110,
                    (0,0):      0b1111
            }
    ADDR_PRE_WLP = 0b00011 << 2
    ADDR_WLP = { 1:     0b00,
                 'NC':  0b10,
                 0:     0b11
            }
    D_REF = {   "EXT":  0b00,
                2.5:    0b01,
                2.048:  0b10,
                4.096:  0b11
            }
    D_POWER = {
                'A':    0b0000,
                'B':    0b0001,
                'C':    0b0010,
                'D':    0b0011,
                'ALL':  0b1000
            }
    D_CHANNEL = {
                'A':    0b0001,
                'B':    0b0010,
                'C':    0b0100,
                'D':    0b1000
            }
    D_PULLDOWN = {  'NORMAL':   0b00,
                    '1k':       0b01,
                    '100k':     0b10,
                    'HZ':       0b11
            }
    CMD_REF     = 0b01110 << 3
    CMD_POWER   = 0b010000 <<2
    CMD_CODE    = 0b0000 << 4
    CMD_LOAD    = 0b0001 << 4
    CMD_CODE_LOAD     = 0b0011 << 4      
    CMD_CODE_LOAD_ALL = 0b0010 << 4
    CMD_CONFIG  = 0b0110 << 4
    CMD_SW_RESET= 0b01010001
    CMD_SW_CLEAR= 0b01010000

    ext_vref = 2e-3 # default value. Slightly strange to notice if it was changed.


    def __init__(self, addr1, addr0,
                gateway,
                i2c_mux,
                package="TSSOP", 
                n_bits=12, 
                name="MAX5815 DAC",
                emulate = False
                ):  

        """ I2C address is calculated from the ADDR1:0 pins states """
        assert package in ["TSSOP","WLP"]
        assert addr0 in [0,1]
        assert addr1 in [0,1]
        assert n_bits in [8,10,12]
        self.n_bits = n_bits
        self.lsb    = None
        self.i2c_mux = i2c_mux
        # slave address of the device is hardwired
        if package == "TSSOP":
            self.address = self.ADDR_PRE_TSSOP + self.ADDR_TSSOP[(addr1,addr0)]
        if package == "WLP":
            self.address = self.ADDR_PRE_WLP + self.ADDR_WLP[addr0]
        super().__init__(addr=self.address, gateway=gateway, name=name)
        self.emulate = emulate

    def voltage2code(self, voltage):
        """ ext_ref is the external voltage supplied to the chip. Used only if the DAC is configured with external reference. """
        ref = self.get_reference()
        assert ref in self.D_REF.keys()
        if ref == "EXT":
            ref = self.ext_vref
        # assert ref != 0
        if ref == 0:
            """ should happen only for emulation testing. """
            return 0x00ff
        else:
            lsb = ref / pow(2, self.n_bits)
            return round(voltage / lsb )

    def code2voltage(self, code):
        ref = self.get_reference()
        logger.debug("REF: %r" %ref)
        assert ref in self.D_REF.keys()
        assert float(code).is_integer(), "Argument 'code' is not an integer."
        assert 0 <= code < (1 << self.n_bits), "Argument 'code'=%#x is out of range. 'code' < %#x" % (code, 1 << self.n_bits)
        lsb = ref/pow(2, self.n_bits)
        return code * lsb

    def set_reference(self, ref=2.5, rf2=0, ext_vref=1e-3):   
        """ Sets the voltage reference used by the DAC.
        ref:         rf2: 0: reference powered down when DAC powered down. 1: always on.

        When an internal reference is selected, that voltage is 
        available on the REF pin for other external circuitry 
        and can drive a 25kOhm load.

        Paramteres
        ----------
        ref : dictionary keys
            Possible values: 'EXT', 2.5, 2.048, 4.096
        rf2 : int
            0: reference powered down when DAC powered down. 1: always on.
        ext_vref: float
            The value of the external reference voltage connected to the DAC. Needed for calculations.
        """

        assert ref in self.D_REF.keys(), "%r with type %r is not in %r" %(ref, type(ref), self.D_REF.keys())
        # MAX581x accepts/needs 3 bytes of data writes.
        self.write( reg=self.CMD_REF + (rf2 << 2) + self.D_REF[ref], data=0x0000, ndata=2 )    # Only 1 command byte
        if ref == "EXT":
            self.ext_vref = ext_vref


    def get_reference(self, return_bits=False):
        """ Get the reference setting from the DAC chip """
        if self.emulate:
            ref_bits = random.randint(1,3)  # 0, i.e. EXT is not allowed
        else:
            ref_bits = self.read( reg = self.CMD_REF, ndata = 2 )  & 0x0003 # returns the two LSB of the two byte data
        if return_bits:
            return ref_bits
        else:
            return next(key for key,value in self.D_REF.items() if value == ref_bits)
    
    def set_code(self, code, channel):
        assert channel in self.D_CHANNEL.keys(), "Invalid DAC channel number. Valid values are " +  ", ".join(self.D_CHANNEL.keys())
        assert 0 <= code <= (1<<self.n_bits), "DAC code=%#x is out of range. It supposed to be a 12 bit number." % (code)
        self.write(reg = self.CMD_CODE_LOAD + self.D_CHANNEL[channel], data = (code << 4), ndata = 2)

    def get_code(self, channel):
        assert channel in self.D_CHANNEL.keys(), "Invalid DAC channel number. Valid values are: " + ", ".join(self.D_CHANNEL.keys())
        if self.emulate:
            logger.debug("!!!EMULATION MODE!!!")
            return random.randint(0,(1<<self.n_bits)-1)
        else:
            # my_reg = self.CMD_CODE + (1<<self.D_CHANNEL[channel])
            my_reg = self.CMD_LOAD + (1<<self.D_CHANNEL[channel])
            logger.debug("REG: 0x{:02x} for ch={} code".format(my_reg,channel))
            my_code = self.read(reg = my_reg, ndata = 2) >>4
            logger.debug("CH{} CODE=0x{:02x}".format(channel,my_code))
            return my_code

    def set_voltage(self, voltage, channel):
        """ Set the desired voltage to the DAC output. """
        self.set_code(self.voltage2code(voltage), channel=channel)

    def get_voltage(self, channel):
        assert channel in self.D_CHANNEL.keys(), "Invalid DAC channel number. Valid values are: " + ", ".join(self.D_CHANNEL.keys())
        return self.code2voltage(self.get_code(channel))

    def sw_reset(self):
        """ reset all CODE, DAC, and configuration registers to their default values. """
        self.write(reg = self.CMD_SW_RESET, data = 0x00, ndata=0)

    def sw_clear(self):
        """ issue a software clear operation to return all CODE and DAC registers to the zero-scale value. """
        self.write(reg = self.CMD_SW_CLEAR, data= 0x00, ndata=0)
     
    def set_power(self, dac, state=1, pd_mode='NORMAL'):
        """ Sets the power mode of the selected DACs """
        assert dac in self.D_POWER.keys()
        assert pd_mode in self.D_PULLDOWN.keys()
        self.write(reg = (self.CMD_POWER + self.D_PULLDOWN[pd_mode]), data =  self.D_POWER[dac], ndata = 1)

    def get_power(self):
        """ Returns with 4 bits for the 4 DAC: D,C,B,A """
        if self.emulate:
            return random.randint(0,15)
        else:
            # The low (2.) byte contains the infor
            pwr = self.read(reg = self.CMD_POWER, ndata = 2) & 0x0f
            return next(key for key,value in self.D_CHANNEL.items if value == pwr)
        
