""" Characterization script of the LNBoard

    Measurements
    ------------
    - [ ]   voltage output
            Load current sweep for voltage sweep for multiple references
        - [ ]   voltage output without electrolyte cap (found them noisy in the
      current measurement)
    - [ ]   current sink  
            Sweep output voltage (just few points) for multiple output currents
        - [ ] measure without ekectrolyte cap
    - [ ]   current source
            Sweep output voltage (just few points) for multiple output currents
        - [ ] without electrolyte cap
    - LDO   sweep load vs output voltage

    - [ ]   Statistical measurement in selected points
        - [ ] VDAC [0.4, 0.8, 1.2, 3]; order it vref voltage pairs
            - [ ] w/ elco
            - [ ] w/o elco
        - [ ] Isink
            - [ ] w/ elco
            - [ ] w/o elco
        - [ ] Isource
            - [ ] w/ elco
            - [ ] w/o elco
        - [ ] LDO

"""

import visa, time, datetime, csv, logging, os, sys, pyBP, usb
import instruments.Instrument
from quantiphy import Quantity
from instruments.Keysight_B2912A import Keysight_B2912A
from LowNoiseBoard import LNBoard

def init_smu(smu):
    smu.full_reset()
    smu.set_measure_power_line_cycles(nplc=4)
    smu.configure_voltage_source(voltage=0,channel=1)
    smu.configure_voltage_source(voltage=0,channel=2)

# if __name__ == "main":
if True:    
    # Initialize logger
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
    logger = logging.getLogger("LNBoard")
    # logger of other modules
    instruments.Instrument.logger.setLevel(logging.ERROR)
    Keysight_B2912A.logger.setLevel(logging.ERROR)
    visa.logger.setLevel(logging.ERROR)
    
    t_script_start = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    meas_date = time.strftime("%Y_%m_%d")      

    def Buspirate_init():
        ##########################################
        # PC - Board interface definition
        ##########################################
        #   It is possible to use multiple PC-to-I2C/SPI/etc. gateways, therefore for every instance 
        # the gateway instance needs to be defined
        i2c_gateway = pyBP.I2Chigh()
        i2c_gateway.speed = '400kHz'
        i2c_gateway.configure(power=True, pullup=True)

        return i2c_gateway

    LN = LNBoard(i2c_gateway=Buspirate_init())

    LN.dac_vref.set_reference(ref=2.5, rf2=1)
    LN.dac_iref.set_reference(ref=2.048, rf2=1)
    LN.isource_A.set_current(100e-6, voltage=1.024)
   
    rm = visa.ResourceManager()
    print(rm.list_resources())
    
    smu_usb = "USB::2391::36376::MY51142629::0::INSTR"
    inst = rm.open_resource(smu_usb)
    
    # smu  = Keysight_B2912A(addr="TCPIP0::172.31.228.86::inst0::INSTR",current_limit=1, voltage_limit=6)
    smu  = Keysight_B2912A(addr=smu_usb ,current_limit=1, voltage_limit=6)

    # config the trace buffer here
    # how to trigger?
    smu.config_sweep(IVmode="voltage", start=0, stop=5, points=100)
    a = smu.read_array(ch=1)

