
class ldo():
    """ Class for LT3042 and similar LDO's based on a follower opamp
    configuration with a current source to set the output voltage on an
    external resistor. """
    def __init__(self, rheo, isource):
        # TODO: remove it. It accepts an abstracted rheo
        self.rheo    = rheo
        self.isource = isource

    def set_voltage(self, voltage):
        """ Set LDO output voltage.
            The output voltage is isource*R
        """
        self.rheo.set_res(res=voltage/self.isource)
    
    def get_voltage(self):
        return self.rheo.get_res()*self.isource

