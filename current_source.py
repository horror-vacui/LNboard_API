import logging
logger = logging.getLogger(__name__)

class current_source():
    """ Class for current sink Iout = Vdac/R 
        
        This class is to be used for current sink and source. The current value
        is independent of the sign of the current set. 

        By overlapping resistance values, the rhoestat with the 
        smallest LSB distance from the middle value will be used

        100k's LSB = 391Ohm ~= 13 LSB of 5k
        5k's LSB   = 19.5Ohm

    """

    def __init__(self, dac, rheo_5, rheo_100, gpio_pin):
        self.dac       = dac
        self.rheo_5    = rheo_5
        self.rheo_100  = rheo_100
        self.gpio_pin  = gpio_pin   # gpio extender device
        self.L_RANGE   = [rheo_5.fullscale, rheo_100.fullscale, "low", "high"]
    
    def set_current(self, current, voltage=None):
        """ Sets the output current
        
        Parameters:
        ----------
            voltage: float
                the reference voltage to be used
            current: float
                the desired output current
                """
        if voltage == None:
            # use the current (=actual) voltage setting
            vref = self.dac.get_voltage()
        else:
            self.dac.set_voltage(voltage)
            vref = voltage
        res = vref/current
        logger.debug(f"I=f{current}, V=f{voltage}, R={res}")
        
        # distance from the middle code:
        if res < self.rheo_5.fullscale:
            d_mid_100 = abs(self.rheo_100.res2code(res) - (1 << (self.rheo_100.n_bits-1)))
            d_mid_5   = abs(self.rheo_5.res2code(res)   - (1 << (self.rheo_5.n_bits-1)))

            logger.debug(f"Difference from middle point code: {d_mid_5} and {d_mid_100} for 5 and 100k rheo, respectively")
            if d_mid_100 < d_mid_5:
                # the resistance is closer to the mid value of the 100k rheo
                self.rheo_100.set_res(res) 
                self.gpio_pin.set(1) # switch to 100k rheo
            else:
                self.rheo_5.set_res(res) 
                self.gpio_pin.set(0) # switch to 5k rheo
        else:
            logger.debug(f"Setting the 100k rheo to {res}. GPIO=1")
            self.rheo_100.set_res(res) 
            self.gpio_pin.set(1) # switch to 100k rheo
        
    def get_current(self, detailed=False):
        """ Returns the current
        
            Paramters
            ---------
            detailed:   bool
                        If True it returns a list of [I, V, R]
                        """
        if self.gpio_pin.get() == 1:
            rheo = self.rheo_100
        else:
            rheo = self.rheo_5
        voltage = self.dac.get_voltage()
        resistance = rheo.get_res()
        current = voltage/resistance
        if detailed:
            rtn = [current, voltage, resistance]
        else:
            rtn = current
        return rtn
            
