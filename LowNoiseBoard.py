# DO_EMULATE = True 
DO_EMULATE = False

import i2c, pyBP, random, logging, sys
from functools import partial,wraps
# importing from the chip modules
from max5815 import max5815
from pca9542a import pca9542a
from mcp466x import mcp466x
from mcp23x08 import mcp23008
from gpio import *
from rheostat import rheostat
from ldo import ldo
from current_source import current_source
from dac import dac

########################################################################
# Class definition
########################################################################

class LNBoard():
    def __init__(self, i2c_gateway):
        self.i2c_gateway = i2c_gateway
    
        self.i2c_mux = pca9542a(i2c_gateway)
        ########################################################################
        # Chip definitions
        ########################################################################
        self.dac_vref         = self.max5815_ch(addr1=0, addr0=0, gateway=i2c_gateway,
                                    package="TSSOP", n_bits=12, name="voltage reference DAC",
                                    func=self.deco_func_i2c_channel0   )        
        self.dac_iref         = self.max5815_ch(addr1=0, addr0=1, gateway=i2c_gateway,
                                    package="TSSOP", n_bits=12, name="current reference DAC",
                                    func=self.deco_func_i2c_channel0   )        

        self.gpio_dev         = self.mcp23008_ch(gateway=i2c_gateway, addr2=0, addr1=0, addr0=0,    
                                    n_bits=8, name="GPIO extender", func=self.deco_func_i2c_channel0 ) 
        self.gpio_dev.set_io_dir(0xf0) # set the bottom four bits as outputs.

        self.rheo_dev_ldo     = self.mcp466x_ch( gateway=self.i2c_gateway, addr1=0, addr0=0, 
                                        fullscale=50e3, n_bits=8,  
                                        name="LDO rheostat",
                                        func=self.deco_func_i2c_channel1   )
        self.rheo_dev_isink_5  = self.mcp466x_ch( gateway=self.i2c_gateway, addr1=0, addr0=0, 
                                        fullscale=5e3, n_bits=8, 
                                        name="Current sink 5kOhm rheostat",
                                        func=self.deco_func_i2c_channel0   )
        self.rheo_dev_isink_100 = self.mcp466x_ch(gateway=self.i2c_gateway, addr1=0, addr0=1, 
                                        fullscale=100e3, n_bits=8, 
                                        name="Current sink 100kOhm rheostat",
                                        func=self.deco_func_i2c_channel0   )
        self.rheo_dev_isource_5 = self.mcp466x_ch(gateway=self.i2c_gateway, addr1=1, addr0=0, 
                                        fullscale=5e3,   n_bits=8, 
                                        name="Current source 5kOhm rheostat",
                                        func=self.deco_func_i2c_channel0   )
        self.rheo_dev_isource_100 = self.mcp466x_ch(gateway=self.i2c_gateway, addr1=1, addr0=1, 
                                        fullscale=100e3, n_bits=8, 
                                        name="Current source 100kOhm rheostat",
                                        func=self.deco_func_i2c_channel0   )

        ##########################################
        # Abstract/derived component definitions
        ##########################################
        # The order of the outputs in the Board does not follow the DAC channels
        # The DAC naming in the board is therefore different
        self.dac_va   = dac(device=self.dac_vref, channel='B')
        self.dac_vb   = dac(device=self.dac_vref, channel='A')
        self.dac_vc   = dac(device=self.dac_vref, channel='D')
        self.dac_vd   = dac(device=self.dac_vref, channel='C')

        self.dac_ia   = dac(device=self.dac_iref, channel='A')
        self.dac_ib   = dac(device=self.dac_iref, channel='B')
        self.dac_ic   = dac(device=self.dac_iref, channel='C')
        self.dac_id   = dac(device=self.dac_iref, channel='D')

        self.board_gpio         = gpio( gpio_dev=self.gpio_dev, bit_offset=4 )
        self.gpio_isource_A     = gpio_pin( gpio=self.gpio_dev, n_bit=2 )
        self.gpio_isource_B     = gpio_pin( gpio=self.gpio_dev, n_bit=3 )
        self.gpio_isink_A       = gpio_pin( gpio=self.gpio_dev, n_bit=0 )
        self.gpio_isink_B       = gpio_pin( gpio=self.gpio_dev, n_bit=1 )

        self.rheo_isource_A_5   = rheostat( device=self.rheo_dev_isource_5,   channel=1 )
        self.rheo_isource_A_100 = rheostat( device=self.rheo_dev_isource_100, channel=1 )
        self.rheo_isource_B_5   = rheostat( device=self.rheo_dev_isource_5,   channel=0 )
        self.rheo_isource_B_100 = rheostat( device=self.rheo_dev_isource_100, channel=0 )
        self.rheo_isink_A_5     = rheostat( device=self.rheo_dev_isink_5,     channel=0 )
        self.rheo_isink_A_100   = rheostat( device=self.rheo_dev_isink_100,   channel=0 )
        self.rheo_isink_B_5     = rheostat( device=self.rheo_dev_isink_5,     channel=1 )
        self.rheo_isink_B_100   = rheostat( device=self.rheo_dev_isink_100,   channel=1 )
        self.rheo_ldo_a         = rheostat( device=self.rheo_dev_ldo,         channel=1 )
        self.rheo_ldo_b         = rheostat( device=self.rheo_dev_ldo,         channel=0 )

        self.isource_A        = current_source(      # S_A
                                dac         = self.dac_ic, 
                                rheo_5      = self.rheo_isource_A_5, 
                                rheo_100    = self.rheo_isource_A_100, 
                                gpio_pin    = self.gpio_isource_A
                                )
        self.isource_B        = current_source(      # S_B
                                dac         = self.dac_id, 
                                rheo_5      = self.rheo_isource_B_5, 
                                rheo_100    = self.rheo_isource_B_100, 
                                gpio_pin    = self.gpio_isource_B
                                )
        self.isink_A         = current_source(      
                                dac         = self.dac_ia, 
                                rheo_5      = self.rheo_isink_A_5, 
                                rheo_100    = self.rheo_isink_A_100, 
                                gpio_pin    = self.gpio_isink_A
                                )
        self.isink_B         = current_source(      
                                dac         = self.dac_ib, 
                                rheo_5      = self.rheo_isink_B_5, 
                                rheo_100    = self.rheo_isink_B_100, 
                                gpio_pin    = self.gpio_isink_B
                                )

        self.ldo_a       = ldo(rheo=self.rheo_ldo_a, isource=100e-6)
        self.ldo_b       = ldo(rheo=self.rheo_ldo_b, isource=100e-6)

    ############################################################################
    # Define some decorators for adding I2C subchannels to the device classes  #
    ############################################################################
    def deco_func_i2c_channel0(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Yep, its global. I found no satisfactory way to add an argument to the decorator
            self.i2c_mux(0)          
            return func(*args, **kwargs)
        return wrapper

    def deco_func_i2c_channel1(self, func):
        @wraps(func)
        def wrapper(*args,**kwargs):
            self.i2c_mux(1)          
            return func(*args, **kwargs)
        return wrapper

    class max5815_ch(max5815):
        def __init__(self, func, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.deco_func = func
            logger.debug("Decorator function for %s: %s" % (type(self).__name__,self.deco_func.__name__))

            func_list = ['write','read']
            for i in func_list:
                setattr(self, i, self.deco_func(getattr(self, i)))

    class mcp23008_ch(mcp23008):
        def __init__(self, func, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.deco_func = func
            logger.debug("Decorator function for %s: %s" % (type(self).__name__,self.deco_func.__name__))
            
            func_list = ['write','read']
            for i in func_list:
                setattr(self, i, self.deco_func(getattr(self, i)))

    class mcp466x_ch(mcp466x):
        def __init__(self, func, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.deco_func = func
            logger.debug("Decorator function for %s: %s" % (type(self).__name__,self.deco_func.__name__))
            
            func_list = ['write','read']
            for i in func_list:
                setattr(self, i, self.deco_func(getattr(self, i)))


############################################################################
# End of Class definition of LNBoard                                       # 
############################################################################
if __name__ == "__main__":
    """ Configures BusPirate and sets up some default value for all outputs. """

    # Initialize logger
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
    logger = logging.getLogger("LNBoard")

    def Buspirate_init():
        ##########################################
        # PC - Board interface definition
        ##########################################
        #   It is possible to use multiple PC-to-I2C/SPI/etc. gateways, therefore for every instance 
        # the gateway instance needs to be defined
        i2c_gateway = pyBP.I2Chigh()
        i2c_gateway.speed = '400kHz'
        i2c_gateway.configure(power=True, pullup=True)
        # TODO: add here a check about I2C bus status

        """BusPirate sensed a short to due to the capacitances(?) on the board.
        First BP Supply should be started, and only after that can we 
        connect the board"""
        # input("Connect the 5V to the LowNoiseBoard")
        
        return i2c_gateway

    
    LN = LNBoard(i2c_gateway=Buspirate_init())
    
    LN.dac_vref.set_reference(2.5)
    logger.debug("DAC_VREF REF: %r" % LN.dac_vref.get_reference())
    logger.debug("DAC_VREF A CODE=0xabc")
    LN.dac_vref.set_code(code=0xabc, channel="A")
    logger.debug("DAC_VREF A CODE={:03x}".format(LN.dac_vref.get_code(channel="A")))

    LN.dac_vref.set_reference(ref=2.5, rf2=1)

    LN.dac_iref.set_reference(ref=2.048, rf2=1)

    LN.dac_vd.set_voltage(0.25)
    LN.dac_va.set_voltage(0.5)
    LN.dac_vb.set_voltage(0.75)
    LN.dac_vc.set_voltage(1.00)
    print("DAC_A voltage was set to: %r" % LN.dac_va.get_voltage())

    LN.ldo_a.set_voltage(0.4)
    LN.ldo_b.set_voltage(0.2)
    print("LDO_A voltage was set to: %r" % LN.ldo_a.get_voltage())

    LN.isource_A.set_current(100e-6, voltage=1.024)
    LN.isource_B.set_current(10e-3, voltage=2.0)
    LN.isink_A.set_current(50e-6, voltage=1.024)
    LN.isink_B.set_current(5e-3, voltage=2.0)

    
