from smbus import SMBus

BUS = 1

# slave addresses per i2cdetect
PULSEOX_ADDR = 0x57
ACCEL_ADDR = 0x19

# assorted register addresses
INT_STAT_1 = 0x00
INT_STAT_2 = 0x01
FIFO_WR_PTR = 0x04
FIFO_OVF = 0x05
FIFO_RD_PTR = 0x06
FIFO_DATA = 0x07
FIFO_CONFIG = 0x08
MODE_CONFIG = 0x09
SPO2_CONFIG = 0x0A
LED1_PA = 0x0C 
LED2_PA = 0x0D
LED3_PA = 0x0E
LED4_PA = 0x0F
TEMP_INT = 0x1F
TEMP_FRAC = 0x20

class MAX30101():
    def __init__(self):
        """
        set up for pulseOx mode
        """
                
        self.bus = SMBus(BUS)

    def reset(self):
        """
        triggers reset on device, returns all registers to startup conditions (mostly 0x00 for all)
        """
        reset_byte = self.bus.read_byte_data(PULSEOX_ADDR, MODE_CONFIG)
        reset_byte |= 0x40
        self.bus.write_byte_data(PULSEOX_ADDR, MODE_CONFIG, reset_byte) 
        
dev = MAX30101()
dev.reset()
