from smbus import SMBus
import time
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np

# number of samples we want to read at a time (note 1 sample = 6 bytes in SpO2 mode)
NUM_SAMPLES = 1

# number of bytes in 1 sample for SpO2 Mode is 6
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

class MAX30101():
    def __init__(self):
        """
        set up for pulseOx mode
        """
                
        self.bus = SMBus(BUS)
        
        # reset
        self.reset()
      
        # set to SpO2 mode
        self.spo2_mode()
        
        # self.set_leds(1)
        
        # for wrist
        self.set_leds(20)
        
        # # most of these are taken from default settings on software, besides sample rate
        # # Pulse Width: 411 us; Sample Rate: 50 Hz; ADC Full Scale Range: 8192 nA, averaging 2 samples
        self.set_adc_range(3)
        self.set_sample_rate(1)
        self.set_pulse_width(2) 
        self.set_sample_avg(2)
        self.set_overflow(1)

        # # tested -- work pretty good on finger
        # self.set_adc_range(3)
        # self.set_sample_rate(1)
        # self.set_pulse_width(3) 
        # self.set_sample_avg(2)
        # self.set_overflow(1)

        
    def test(self):
        """
        function used for debugging
        """
        write_ptr = self.bus.read_byte_data(PULSEOX_ADDR, FIFO_WR_PTR) & 0x1F
        read_ptr = self.bus.read_byte_data(PULSEOX_ADDR, FIFO_RD_PTR) & 0x1F
        if write_ptr >= read_ptr:
            available_samples = write_ptr - read_ptr
        else:
            available_samples = 31 - read_ptr + write_ptr
        if available_samples >= 1:
            data = self.bus.read_i2c_block_data(PULSEOX_ADDR, FIFO_DATA, SAMPLE_SIZE)
        print(write_ptr, read_ptr)
        
    def is_data_ready(self):
        """
        Check if there is enough data stored in the FIFO for us to read
        """
        write_ptr = self.bus.read_byte_data(PULSEOX_ADDR, FIFO_WR_PTR) & 0x1F
        read_ptr = self.bus.read_byte_data(PULSEOX_ADDR, FIFO_RD_PTR) & 0x1F 
        # print(write_ptr, read_ptr)
        
        # number of available samples calc needs to account for pointer wraparound
        if write_ptr >= read_ptr:
            available_samples = write_ptr - read_ptr
        else:
            available_samples = 32 - read_ptr + write_ptr
        return (available_samples >= NUM_SAMPLES)

    def read_data(self):
        """
        Read data from FIFO with processing (ie. separating red and IR led data)
        """
        # make sure we have enough data to read
        while not self.is_data_ready():
            continue

        data = self.bus.read_i2c_block_data(PULSEOX_ADDR, FIFO_DATA, SAMPLE_SIZE)

        # convert ints to hex format
        data = list(map(lambda x: "0x{:02x}".format(x), data))
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

    def plot_waveform(self):
        # plot waveform - adapted from stackoverflow.com/questions/45046239/python-realtime-plot-using-pyqtgraph
        app = QtGui.QApplication([])
        
        win = pg.GraphicsWindow(title='PulseOx Data')
        win.resize(1000,600)
        win.setWindowTitle('Waveform Data')
        
        p1 = win.addPlot(title='Waveform Data')
        redCurve = p1.plot()
        irCurve = p1.plot()
        # good window range for on idx finger
#        p1.setRange(yRange=(20000,22000))

  #      p1.setRange(yRange=(40000,45000))

        windowWidth = 100
        redData = np.linspace(0,0,windowWidth)
        irData = np.linspace(0,0,windowWidth)
        
        ptr = windowWidth - 1 # pointer to where data is added to our plot
        
        # enable antialiasing
        pg.setConfigOptions(antialias=True)
        
        # realtime data plotting
        while True:
            # update data
            dataPoint = self.read_data()
            redData[ptr] = dataPoint[0]
            irData[ptr] = dataPoint[1]
            # shift data windows one to the left
            redData[:-1] = redData[1:]
            irData[:-1] = irData[1:]
            
            # update plot
            redCurve.setData(redData)
            irCurve.setData(irData)
            QtGui.QApplication.processEvents()
        
        # close Qt
        pg.QtGui.QApplication.exec_()

    def set_sample_avg(self, level):
        """
        Sets number of samples averaged per FIFO sample

        Key:
        0 -> 1 samples averaged
        1 -> 2 samples averaged
        2 -> 4 samples averaged
        3 -> 8 samples averaged
        4 -> 16 samples averaged
        5 -> 32 samples averaged

        More samples averaged reduces rate of data output.
        """
        if level not in range(6):
            print('Invalid input')
            return
        
        fifo_config = self.bus.read_byte_data(PULSEOX_ADDR, FIFO_CONFIG)
        if level == 0:
            fifo_config &= 0x1F
        elif level == 1:
            fifo_config = ((fifo_config | 0x20) & 0x3F)
        elif level == 2:
            fifo_config = ((fifo_config | 0x40) & 0x5F)
        elif level == 3:
            fifo_config = ((fifo_config | 0x60) & 0x7F)
        elif level == 5:
            fifo_config = ((fifo_config | 0x80) & 0x9F)
        else:
            fifo_config |= 0xE0
        self.bus.write_byte_data(PULSEOX_ADDR, FIFO_CONFIG, fifo_config)
        
    def spo2_mode(self):
        """
        Set's MAX30101 to SPO2 mode
        """
        mode_byte = self.bus.read_byte_data(PULSEOX_ADDR, MODE_CONFIG) & 0xFF
        mode_byte = ((mode_byte | 0x03) & 0xFB)
        self.bus.write_byte_data(PULSEOX_ADDR, MODE_CONFIG, mode_byte)

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
            adc_range &= 0x9F
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
            pulse = ((pulse | 0x01) & 0xFD)
        elif level == 2:
            pulse = ((pulse | 0x02) & 0xFE)
        else:
            pulse |= 0x3

        self.bus.write_byte_data(PULSEOX_ADDR, SPO2_CONFIG, pulse)

    def set_leds(self, current):
        """
        current is in mA and can must be between 0 and 51 (in mA), inclusive
        """
        if current > 51 or current < 0:
            print('Invalid Input')
            return
        led_reg = int(current / 0.2)
        self.bus.write_byte_data(PULSEOX_ADDR, LED1_PA, led_reg)
        self.bus.write_byte_data(PULSEOX_ADDR, LED2_PA, led_reg)

    def set_overflow(self, mode):
        """
        mode = 0: FIFO stops getting data upon overflow
        mode = 1: FIFO starts replacing old data upon overflow
        """
        if mode not in range(2):
            print('Invalid Input')
            return
        
        rollover = self.bus.read_byte_data(PULSEOX_ADDR, FIFO_CONFIG)
        if mode == 0:
            rollover &= 0xEF
        else:
            rollover |= 0x10
        self.bus.write_byte_data(PULSEOX_ADDR, FIFO_CONFIG, rollover)
            

    def reset(self):
        """
        triggers reset on device, returns all registers to startup conditions (mostly 0x00 for all)
        """
        reset_byte = self.bus.read_byte_data(PULSEOX_ADDR, MODE_CONFIG)
        reset_byte |= 0x40
        self.bus.write_byte_data(PULSEOX_ADDR, MODE_CONFIG, reset_byte) 
         
pulseOx = MAX30101()
pulseOx.plot_waveform()
x = []
for i in range(100):
    data = pulseOx.read_data()
    #print(data)
pulseOx.reset()

# #print(red)

