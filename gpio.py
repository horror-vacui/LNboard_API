import logging, sys
logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class gpio():
    """ An abstraction layer above the device level GPIO to take into account
    any used GPIO pins, and restart their numbering.

    Attributes
    ----------
    device:     gpio_dev
                The GPIO chip level device, which configures the GPIOs. It
                needs to have methods 'get_gpio()', 'set_gpio(value)'.
                'get_gpio_bit(idx_bit)' and 'set_gpio_bit(idx_bit, value)'.
    bit_offset: int
                Offset in numbering compared to the GPIO device's internal
                numbering
    eff_bits:   int
                The effective number of bits which are free to use in this
                class
    """

    def __init__(self, gpio_dev, bit_offset=0):
        self.device     = gpio_dev
        self.bit_offset = bit_offset
        self.eff_bits   = gpio_dev.n_bits - bit_offset

    def get_gpio(self):
        return (self.device.get_gpio() >> self.bit_offset)

    def set_gpio(self, value):
        """ Sets the GPIO register to the desired value """
        self.device.set_gpio(value = (value << self.bit_offset))

    def get_gpio_bit(self, n_bit):
        assert 0<=n_bit<self.eff_bits, f"Pin number f{n_bit}is out of range.  Valid range is 0..{self.eff_bits}"
        return self.device.get_gpio_bit(idx_bit=(n_bit + self.bit_offset))

    def set_gpio_bit(self, n_bit, value):
        assert 0<=n_bit<self.eff_bits, f"Pin number f{n_bit}is out of range.  Valid range is 0..f{self.eff_bits}"
        self.device.set_gpio_bit(idx_bit=(n_bit+self.bit_offset), value=(value & 1))

class gpio_pin():
    """ An abstraction class for one GPIO bit."""

    def __init__(self, gpio, n_bit):
      self.gpio_obj = gpio
      self.n_bit    = n_bit

    def set(self, value=1):
      """ Set the the bit value to "value" """
      self.gpio_obj.set_gpio_bit(self.n_bit, value)

    def reset(self):
      """ Reset, i.e. set the the bit to 0 """
      self.set(0)

    def get(self):
      """ Returns the the bit value """
      return self.gpio_obj.get_gpio_bit(self.n_bit)

