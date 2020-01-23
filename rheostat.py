class rheostat():
    """ Virtual rheostat. Physical rheostats have multiple channels. This wrapper class 
        eases the use of rheostats by creating separate virtual instances for every 
        channel.  """

    def __init__(self, device, channel):
        self.device  = device   # rheostat ic
        self.channel = channel  # rheostat channel
        self.fullscale    = device.fullscale
        self.n_bits       = device.n_bits
        self.res_step     = device.res_step
        self.res2code     = device.res2code
        
    def set_res(self, res):
        """ Set the desired resistance value """
        self.device.set_res(res=res, channel=self.channel)

    def get_res(self):
        """ Get the current resistance value """
        return self.device.get_res(channel=self.channel)

    def inc(self):
        """ Increment the resistance value by 1 LSB """
        self.device.inc_wiper(channel=self.channel)      

    def dec(self):
        """ Increment the resistance value by 1 LSB """
        self.device.dec_wiper(channel=self.channel)      

