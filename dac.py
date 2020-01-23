import random, logging
logger = logging.getLogger(__name__)

class dac():
    """ One virtual dac for every max5815 channel.
        The DACs in a chip are sharing the same reference,
        and thus they are not completely independent.

        Therefore the reference setting should happen 
        at the chip level, and not in this class. 
        """

    def __init__(self, device, channel):
        # Probably more general dac commands could have been developed and used.
        # even the variable name indicates that this code was developed for max5815.
        assert channel in ['A','B','C','D']
        self.device  = device
        self.channel = channel

    def set_code(self, code):
        self.device.set_code(code = code, channel = self.channel)

    def set_voltage(self, voltage):
        self.device.set_voltage(voltage = voltage, channel = self.channel)

    def get_voltage(self):
        return self.device.get_voltage(self.channel)

    def get_code(self):
        return self.device.get_code(channel = self.channel)

    def set_power(self, pd_mode='NORMAL'):
        """ Set power mode of the DAC. The Power-Down Mode is a chip level
        command, all four channels are affected.
        
            Paramter
            --------
            pd_mode:    string
                        Pull-down resistor in power-down mode: 'NORMAL', '1k', '100k', 'HZ'.
                        
        """

        """ It is not written in the datasheet how can the PDmode information
        accessed... """
        # if pd_mode=None:
            # # read out the current pd_mode
            # self.device.get_power
        # TODO: rewrite the function in max5815.py, to allow channel-wise 
        # setting of the power mode. 
        self.device.set_power(dac = self.channel, pd_mode=pd_mode)


