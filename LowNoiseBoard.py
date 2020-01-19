# DO_EMULATE = True 
DO_EMULATE = False

import i2c, pyBP, random, logging, sys
from functools import partial,wraps
# importing from the chip modules
from max5815 import max5815
from pca9542a import pca9542a
from mcp466x import mcp466x
from mcp23x08 import mcp23008


# Every class has an additional argument: I2C subchannel
# All read and write operation should precede a check of the status

def set_i2c_subchannel(i2c_mux, func_orig):
    def new_func(*args,**kwargs):
        i2c_mux.set_channel(i2c_subchannel)
        rtn = func_orig(*args,**kwargs)
        return rtn
    return new_func

def wrap_i2c_subchannel(cls):
    class NewCls():
        def __init__(self,*args,**kwargs):
            self.oInstance = cls(*args,**kwargs)
        
        def __getattribute__(self,s):
            try:
                x = super().__getattribute__(s)
            except AttributeError:
                pass
            else:
                return x
            x = self.oInstance.__getattribute__(s)
            if type(x) == type(self.__init__): # is is an instance method
                return set_i2c_subchannel(i2c_mux)
            else:
                x
    return NewCls

class BoardLevel_I2C():
    """ 
    wrapper class for devices on the board.
    It contains any additional variables and function, 
    which are not part of the chip level code.

    The code is prepared only for one i2c multiplexer, since it
    is rare to need more subbusses. In those cases another bus
    type might be necessary. If needed a binary tree can be 
    implemented.
    """

    def __init__(self,i2c_channel, i2c_mux):
        assert i2c_channel in [0,1] 
        self.i2c_channel = i2c_channel # dealing with I2C multiplexing 
        self.i2c_mux     = i2c_mux


##########################################################################################################
class ldo(BoardLevel_I2C):
    def __init__(self, rheo, rheo_channel, i2c_channel, i2c_mux):
        self.channel = rheo_channel
        self.rheo    = rheo
        super().__init__(i2c_channel, i2c_mux)

    def set_voltage(self, voltage): 
        self.i2c_mux.set_channel(self.i2c_channel)
        self.rheo.set_res(res=voltage/100e-6, channel=self.channel)
    
    def get_voltage(self):
        self.i2c_mux.set_channel(self.i2c_channel)
        return self.rheo.get_res(channel=self.channel)*100e-6

##########################################################################################################
class rheostat(BoardLevel_I2C):
    """ Virtual rheostat. Physical rheostats have multiple channels. This wrapper class 
        eases the use of rheostats by creating separate virtual instances for every 
        channel.  """
    def __init__(self, rheo_device, rheo_channel, i2c_channel, i2c_mux):
        self.rheo_device  = rheo_device   # rheostat ic
        self.rheo_channel = rheo_channel  # rheostat channel
        super()._init__(i2c_channel, i2c_mux)
        
    def set_res(self, res):
        """ Set the desired resistance value """
        self.i2c_mux.set_channel(self.i2c_channel)
        self.rheo_device.set_res(res=res, channel=self.channel)

    def get_res(self):
        """ Get the current resistance value """
        self.i2c_mux.set_channel(self.i2c_channel)
        return self.rheo_device.get_res(channel=self.channel)

    def inc(self):
        """ Increment the resistance value by 1 LSB """
        self.i2c_mux.set_channel(self.i2c_channel)
        self.rheo_device.inc_wiper(channel=self.channel)      

    def dec(self):
        """ Increment the resistance value by 1 LSB """
        self.i2c_mux.set_channel(self.i2c_channel)
        self.rheo_device.dec_wiper(channel=self.channel)      


##########################################################################################################
class dac(BoardLevel_I2C):
    """ One virtual dac for every max5815 channel.
        The DACs in a chip are sharing the same reference,
        and thus they are not completely independent.

        Therefore the reference setting should happen 
        at the chip level, and not in this class. 
        """

    def __init__(self, max5815, channel, i2c_channel, i2c_mux):
        # Probably more general dac commands could have been developed and used.
        # even the variable name indicates that this code was developed for max5815.
        assert channel in ['A','B','C','D']
        self.device  = max5815
        self.channel = channel
        super().__init__(i2c_channel, i2c_mux)

    def set_code(self, code):
        self.i2c_mux.set_channel(self.i2c_channel)
        self.device.set_code(code = code, channel = self.channel)

    def set_voltage(self, voltage):
        self.i2c_mux.set_channel(self.i2c_channel)
        self.device.set_voltage(voltage = voltage, channel = self.channel)

    def get_voltage(self):
        self.i2c_mux.set_channel(self.i2c_channel)
        return self.device.get_voltage(self.channel)

    def get_code(self):
        self.i2c_mux.set_channel(self.i2c_channel)
        return self.device.get_code(channel = self.channel)

    def set_power(self, pd_mode='NORMAL'):
        self.i2c_mux.set_channel(self.i2c_channel)
        # TODO: rewrite the function in max5815.py, to allow channel-wise 
        # setting of the power mode. 
        self.device.set_power(dac = self.channel, pd_mode=pd_mode)


##########################################################################################################
class current_source(BoardLevel_I2C):
    """ Class for current sink Iout = Vdac/R 
        
        This class is to be used for current sink and source. The current value
        is independent of the sign of the current set. 

        By overlapping resistance values, the rhoestat with the 
        smallest LSB distance from the middle value will be used

        100k's LSB = 391Ohm ~= 13 LSB of 5k
        5k's LSB   = 19.5Ohm

    """
    ############################################################
    # Issue: current = voltage/res
    # Every output has its voltage DAC.
    # There is one voltage reference for all current outputs.
    #   --> reference set to the lowest built-in voltage. 2.048V

    # Design decision:
    # Which is more accurate: rheo or dac in non-middle values? --> DAC is way better
    #   ??? Rheo mode has higher INL, than potentiometer mode. ???
    #   ??? The wiper resistance is 3.5LSB. How is it possible that INL is zero at code 0?
    #   --> I guess their removed that offset from the non-linearity curves

    
    L_RANGE = [5e3, 100e3, "low", "high"]
    LSB_100k = 100e3/2**8
    LSB_5k   = 5e3/2**8
    

    def __init__(self, dac_channel, dac, rheo_5, rheo_100, rheo_channel, i2c_channel, dev_i2c_mux, gpio_pin):
        super().__init__(i2c_channel, dev_i2c_mux)
        self.dac_channel   = dac_channel
        self.dac       = dac
        self.rheo_5    = rheo_5
        self.rheo_100  = rheo_100
        self.gpio_pin  = gpio_pin   # gpio extender device
        self.rheo_channel = rheo_channel # which channel of the rheo is used
    
    def set_current(self, current, voltage=None):
        """ Sets the output curretn
        
        Parameters:
        ----------
            voltage: float
                the reference voltage to be used
            current: float
                the desired output current
                """
        if voltage == None:
            # use the current (=actual) voltage setting
            vref = self.dac.get_voltage(self.dac_channel)
        else:
            self.dac.set_voltage(voltage, channel = self.dac_channel)
            vref = voltage

        res = vref/current
        # NOTE: 100e3 and 5e3 could be saved into the rheo class
        if abs(res-(100e3+self.rheo_100.Rw_typ/2))/self.LSB_100k < abs(res-(5e3+self.rheo_5.Rw_typ/2))/self.LSB_5k:
            # the resistance is closer to the mid value of the 100k rheo
            self.rheo_100.set_res(res) 
            self.gpio_pin.set(1) # switch to 100k rheo
        else:
            self.rheo_5.set_res(res) 
            self.gpio_pin.set(0) # switch to 5k rheo
        
##########################################################################################################
# class gpio(BoardLevel_I2C, mcp23008):
class gpio(BoardLevel_I2C):
    """ To be implemented. Inherit from gpio device class and mask the four used GPIOs. """

    def __init__(self, gpio_dev, dev_i2c_mux, i2c_channel, bit_offset=0):
        super().__init__(i2c_mux=dev_i2c_mux, i2c_channel=i2c_channel)
        self.device     = gpio_dev
        self.bit_offset = bit_offset

    def get_gpio(self):
        self.i2c_mux.set_channel(self.i2c_channel)
        return (self.device.get_gpio() >> self.bit_offset)

    def set_gpio(self, value):
        self.i2c_mux.set_channel(self.i2c_channel)
        self.device.set_gpio(value = (value << self.bit_offset))

    def get_gpio_bit(self, n_bit):
        self.i2c_mux.set_channel(self.i2c_channel)
        return self.device.get_gpio_bit(idx_bit=(n_bit+bit_offset))

    def set_gpio_bit(self, n_bit, value):
        self.i2c_mux.set_channel(self.i2c_channel)
        self.device.set_gpio_bit(idx_bit=(n_bit+self.bit_offset), value=value)

# NOTE: maybe there could be one more abstraction layer, so that single pins will be an independent entity. -> No need to specify in function arguments both the gpio device and its corresponding bit

##########################################################################################################
class gpio_pin():
    """ An abstraction class for one GPIO bit."""

    def __init__(self, gpio, n_bit):
      self.gpio_obj = gpio
      self.n_bit    = n_bit

    def set(self, value):
      """ Set the the bit value to "value" """
      self.gpio_obj.set_gpio_bit(n_bit=self.n_bit, value=value)

    def get(self):
      """ Returns the the bit value """
      return self.gpio_obj.get_gpio_bit(n_bit=self.n_bit)


##########################################################################################################
# END of class definitions
##########################################################################################################
if __name__ == "__main__":
    ##########################################
    # Initialize script
    ##########################################
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
    logger = logging.getLogger(__name__)

    ##########################################
    # PC - Board interface definition
    ##########################################
    #   It is possible to use multiple PC-to-I2C/SPI/etc. gateways, therefore for every instance 
    # the gateway instance needs to be defined
    # i2c_gateway = pyBP.I2C()
    i2c_gateway = pyBP.I2Chigh()
    i2c_gateway.speed = '100kHz'
    i2c_gateway.configure(power=True, pullup=True)
    # TODO: add here a check about I2C bus status

    # input("Connect the 5V to the LowNoiseBoard")

    # It did not work.
    # print(pyBusPirateLite.common_functions.sniff_i2c_devices(bp_device=i2c_gateway, power=True))

    ##########################################
    # Chip definitions
    ##########################################
    i2c_mux = pca9542a(i2c_gateway)
    # define some shorthand functions for channel selection
    # i2c_ch0 = partial(i2c_mux, 0)
    # i2c_ch1 = partial(i2c_mux, 1)

    def wrap_i2c_channel(func, channel):
        @wraps(func)
        def new_func(*args,**kwargs):
            i2c_mux(channel)
            return func(*args, **kwargs)
        return new_func

    dac_vref = max5815(addr1=0, addr0=0, gateway=i2c_gateway, i2c_mux=i2c_mux, package="TSSOP", n_bits=12, name="voltage reference DAC", emulate=DO_EMULATE)        
    dac_iref         = max5815(gateway=i2c_gateway,  addr1=0, addr0=1, i2c_mux=i2c_mux, package="TSSOP", n_bits=12, name="current reference DAC", emulate=DO_EMULATE)        
    gpio_dev         = mcp23008(gateway=i2c_gateway, addr2=0, addr1=0, addr0=0, n_bits=8, name="GPIO extender") 
    rheo_ldo = mcp466x(gateway=i2c_gateway, addr1=0, addr0=0, fullscale=5e3, n_bits=8, name="LDO rheostat")
    rheo_isink_5     = mcp466x(gateway=i2c_gateway, addr1=0, addr0=0, fullscale=5e3,   n_bits=8,  name="Current sink 5kOhm rheostat")
    rheo_isink_100   = mcp466x(gateway=i2c_gateway, addr1=0, addr0=1, fullscale=100e3, n_bits=8,  name="Current sink 100kOhm rheostat")
    rheo_isource_5   = mcp466x(gateway=i2c_gateway, addr1=1, addr0=0, fullscale=5e3,   n_bits=8,  name="Current source 5kOhm rheostat")
    rheo_isource_100 = mcp466x(gateway=i2c_gateway, addr1=1, addr0=1, fullscale=100e3, n_bits=8,  name="Current source 100kOhm rheostat")

    
    ##########################################
    # Abstract/derived components
    ##########################################
    dac_va   = dac(i2c_channel=0, i2c_mux=i2c_mux, max5815=dac_vref, channel='A')
    dac_vb   = dac(i2c_channel=0, i2c_mux=i2c_mux, max5815=dac_vref, channel='B')
    dac_vc   = dac(i2c_channel=0, i2c_mux=i2c_mux, max5815=dac_vref, channel='C')
    dac_vd   = dac(i2c_channel=0, i2c_mux=i2c_mux, max5815=dac_vref, channel='D')
    board_gpio       = gpio(gpio_dev = gpio_dev, dev_i2c_mux = i2c_mux, i2c_channel=0, bit_offset=4)
    gpio_isource_A   = gpio_pin(gpio=board_gpio, n_bit=2)
    gpio_isource_B   = gpio_pin(gpio=board_gpio, n_bit=3)
    gpio_isink_A     = gpio_pin(gpio=board_gpio, n_bit=0)
    gpio_isink_B     = gpio_pin(gpio=board_gpio, n_bit=1)

    isource_A        = current_source(      # S_A
                            dac         = dac_iref, 
                            dac_channel = "B", 
                            rheo_5      = rheo_isource_5, 
                            rheo_100    = rheo_isource_100, 
                            rheo_channel= 1,
                            gpio_pin    = gpio_isource_A,
                            dev_i2c_mux = i2c_mux, 
                            i2c_channel = 0 
                            )
    isource_B        = current_source(      # S_B
                            dac         = dac_iref, 
                            dac_channel = "A", 
                            rheo_5      = rheo_isource_5, 
                            rheo_100    = rheo_isource_100, 
                            rheo_channel= 0,
                            gpio_pin    = gpio_isource_B,
                            dev_i2c_mux = i2c_mux, 
                            i2c_channel = 0 
                            )
    isink_A         = current_source(      
                            dac         = dac_iref, 
                            dac_channel = "C", 
                            rheo_5      = rheo_isink_5, 
                            rheo_100    = rheo_isink_100, 
                            rheo_channel= 1,
                            gpio_pin    = gpio_isink_A,
                            dev_i2c_mux = i2c_mux, 
                            i2c_channel = 0 
                            )
    isink_B         = current_source(      
                            dac         = dac_iref, 
                            dac_channel = "D", 
                            rheo_5      = rheo_isink_5, 
                            rheo_100    = rheo_isink_100, 
                            rheo_channel= 0,
                            gpio_pin    = gpio_isink_B,
                            dev_i2c_mux = i2c_mux, 
                            i2c_channel = 0 
                            )

    ldo_a    = ldo(i2c_channel=1, i2c_mux=i2c_mux, rheo=rheo_ldo, rheo_channel=0)
    ldo_b    = ldo(i2c_channel=1, i2c_mux=i2c_mux, rheo=rheo_ldo, rheo_channel=1)
    
    ##########################################
    # Setting up the devices
    ##########################################
    i2c_mux.set_channel(0)
    dac_vref.set_reference(2.5)
    logger.debug("DAC_VREF REF: %r" % dac_vref.get_reference())
    logger.debug("DAC_VREF A CODE=0xabc")
    dac_vref.set_code(code=0xabc, channel="A")
    logger.debug("DAC_VREF A CODE={:03x}".format(dac_vref.get_code(channel="A")))

    dac_vref.set_reference(ref=2.5, rf2=1)

    dac_iref.set_reference(ref=2.048, rf2=1)

#    rheo_isink_5_A    = rheostat(rheo_device=rheo_isink_5, rheo_channel=1, i2c_channel=0, i2c_mux=i2c_mux)
#    rheo_isink_5_B    = rheostat(rheo_device=rheo_isink_5, rheo_channel=0, i2c_channel=0, i2c_mux=i2c_mux)
#    rheo_isink_100_A  = rheostat(rheo_device=rheo_isink_100, rheo_channel=1, i2c_channel=0, i2c_mux=i2c_mux)
#    rheo_isink_100_B  = rheostat(rheo_device=rheo_isink_100, rheo_channel=0, i2c_channel=0, i2c_mux=i2c_mux)
# rheo code has an automated switching, right?

# NOTE: 
#    - Could the two rheos combined into one object, which could then be used. The range setting could have happen in that object. That would simplify the current source object.
#    - Ideally the top level objects supposed to be fully independent on the lower level implementation.
#    - DAC should be hidden also in an object. The only issue is the reference voltage. So once the reference voltage needs to be changed, the code of the other DAC's should be updated accordingly. --> Their values will not be exactly the same. So reference voltage change should be done only if it is unavoidable. In a GUI a confirmation pop-up will be needed.
# Ideally a current source should get only a dac and a rheo object.
    


    dac_vd.set_voltage(0.25)
    dac_va.set_voltage(0.5)
    dac_vb.set_voltage(0.75)
    dac_vc.set_voltage(1.00)
    print("DAC_A voltage was set to: %r" % dac_va.get_voltage())

    ldo_a.set_voltage(0.4)
    ldo_b.set_voltage(0.2)
    print("LDO_A voltage was set to: %r" % ldo_a.get_voltage())

    # isource_A.set_current(100e-6, voltage=1.024)
    # isource_B.set_current(10e-3, voltage=2.0)
    # isink_A.set_current(50e-6, voltage=1.024)
    # isink_B.set_current(5e-3, voltage=2.0)

    
