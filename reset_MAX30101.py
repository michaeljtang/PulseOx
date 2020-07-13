from smbus import SMBus

BUS = 1

# slave addresses per i2cdetect
PULSEOX_ADDR = 0x57

# assorted register addresses
MODE_CONFIG = 0x09

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