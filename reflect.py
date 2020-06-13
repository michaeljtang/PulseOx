from smbus import SMBus
import time

# single sample size in SpO2 Mode is 6 bytes
SAMPLE_SIZE = 6

# rpi bus line
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

class ReflectPulseOx():
    def __init__(self):
        """
        set up for pulseOx mode
        """

        self.bus = SMBus(BUS)
        
        # reset
        self.reset()
      
        # set to SpO2 mode
        self.bus.write_byte_data(PULSEOX_ADDR, MODE_CONFIG, 0x03)
        
        # turn on LED's, set to 0.? mA
        self.bus.write_byte_data(PULSEOX_ADDR, LED1_PA, 0x03)
        self.bus.write_byte_data(PULSEOX_ADDR, LED2_PA, 0x03)
        
        # set spo2 settings to default on official software
        # Pulse Width: 411 us; Sample Rate: 1000; ADC Full Scale Range: 8192 nA
        self.bus.write_byte_data(PULSEOX_ADDR, SPO2_CONFIG, 0x57)

    def is_data_ready(self):
        # TODO: pointer wrap-around should be accounted for? not sure if this fxn really works properly
        write_ptr = self.bus.read_byte_data(PULSEOX_ADDR, FIFO_WR_PTR) & 0x1F
        read_ptr = self.bus.read_byte_data(PULSEOX_ADDR, FIFO_RD_PTR) & 0x1F  
 #       print(write_ptr, read_ptr)
        available_samples = write_ptr - read_ptr
 #       print(available_samples)
        return (available_samples >= SAMPLE_SIZE)

    def read_data(self):
        """
        Read data from FIFO
        """
        # TODO: I think the FIFO read pointer needs to be incremented manually? not sure

        # make sure we have enough data to read
        while not self.is_data_ready():
            continue

        # TODO: repeatedly setting mode to SpO2 ensures that data is being collected -- there's prob a better fix
        mode_byte = self.bus.read_byte_data(PULSEOX_ADDR, MODE_CONFIG) & 0xFF
        mode_byte = ((mode_byte | 0x03) & 0xFB)
        self.bus.write_byte_data(PULSEOX_ADDR, MODE_CONFIG, mode_byte)

       
        data = self.bus.read_i2c_block_data(PULSEOX_ADDR, FIFO_DATA, SAMPLE_SIZE)

        # convert ints to hex format
        data = list(map(hex, data))
        # ignore the 0x prefix
        data = list(map(lambda x : x[x.index('x') + 1:], data))
        # combine bytes of data
        red = '0x' + data[0] + data[1] + data[2]
        ir = '0x' + data[3] + data[4] + data[5]
        # convert back to int
        red = int(red, 0)
        ir = int(ir, 0)

#        print(f'red = {red}, ir == {ir}') 
        return (red, ir)

    def set_adc_range(self, level):
        """
        Key: scale parameter to full scale setting...
        0 -> 2048 nA
        1 -> 4096 nA
        2 -> 8192 nA
        3 -> 16384 nA
        """
        if level not in range(4):
            print('Invalid input')
            return

        adc_range = self.bus.read_byte_data(PULSEOX_ADDR, SPO2_CONFIG)
        if level == 0:
            adc_range &= 0x1F
        elif level == 1:
            adc_range = ((adc_range | 0x20) & 0xBF)
        elif level == 2:
            adc_range = ((adc_range | 0x40) & 0xDF)
        else:
            adc_range |= 0x60
        self.bus.write_byte_data(PULSEOX_ADDR, SPO2_CONFIG, adc_range)

    def set_sample_rate(self, level):
        """
        0 = 50 Hz
        1 = 100 Hz
        2 = 200 Hz
        3 = 400 Hz
        4 = 800 Hz
        5 = 1000 Hz
        6 = 1600 Hz
        7 = 3200 Hz
        """
        if level not in range(8):
            print('Invalid Input')
            return
        
        rate = self.bus.read_byte_data(PULSEOX_ADDR, SPO2_CONFIG)
        if level == 0:
            rate &= 0xE3
        elif level == 1:
            rate = ((rate | 0x04) & 0xE7)
        elif level == 2:
            rate = ((rate | 0x08) & 0xEB)
        elif level == 3:
            rate = ((rate | 0x0C) & 0xEF)
        elif level == 4:
            rate = ((rate | 0x10) & 0xF3)
        elif level == 5:
            rate = ((rate | 0x14) & 0xF7)
        elif level == 6:
            rate = ((rate | 0x18) & 0xFB)
        else:
            rate |= 0x1C

        self.bus.write_byte_data(PULSEOX_ADDR, SPO2_CONFIG, rate)

    def set_pulse_width(self, level):
        """
        0 = 69 us
        1 = 118 us
        2 = 215 us
        3 = 411 us
        """
        if level not in range(4):
            print('Invalid Input')
            return

        pulse = self.bus.read_byte_data(PULSEOX_ADDR, SPO2_CONFIG)
        if level == 0:
            pulse &= 0xFC
        elif level == 1:
            pulse = ((pulse | 0x01) & 0xFC)
        elif level == 2:
            pulse = ((pulse | 0x02) & 0xFE)
        else:
            pulse |= 0x3

        self.bus.write_byte_data(PULSEOX_ADDR, SPO2_CONFIG, pulse)

        def set_led(self, current):
        """
        current is in mA and can must be between 0 and 51, inclusive
        """
        
        led_reg = int(current / 0.2)
        self.bus.write_byte_data(PULSEOX_ADDR, LED1_PA, led_reg)
        self.bus.write_byte_data(PULSEOX_ADDR, LED2_PA, led_reg)

    def reset(self):
        """
        triggers reset on device, returns all registers to startup conditions (mostly 0x00 for all)
        """
        reset_byte = self.bus.read_byte_data(PULSEOX_ADDR, MODE_CONFIG)
        reset_byte |= 0x40
        self.bus.write_byte_data(PULSEOX_ADDR, MODE_CONFIG, reset_byte) 
         
pulseOx = ReflectPulseOx()
red = []
ir = []
for i in range(1000):
    data = pulseOx.read_data()
    red.append(data[0])
    ir.append(data[1])
pulseOx.reset()

print(red)

