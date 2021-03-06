# NOTE -- interrupt functionality not implemented in class
# accelerometer functionality not implemented either

from smbus import SMBus
import time
import csv
from datetime import datetime
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np

# number of samples we want to read at a time (note 1 sample = 6 bytes in SpO2 mode)
NUM_SAMPLES = 1

# number of bytes in 1 sample for SpO2 Mode is 6, and 9 for multi-led mode
SPO2_SIZE = 6
MULTI_SIZE = 9

# rpi bus line
BUS = 1

# slave addresses per i2cdetect
PULSEOX_ADDR = 0x57
ACCEL_ADDR = 0x19

# assorted register addresses
INT_STAT_1 = 0x00
INT_STAT_2 = 0x01
INT_ENABLE_1 = 0x02
INT_ENABLE_2 = 0x03
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
MULTI_MODE_1 = 0x11
MULTI_MODE_2 = 0x12
TEMP_INT = 0x1F
TEMP_FRAC = 0x20

class MAX30101():
    def __init__(self, mode='spo2', led=10, adc_range=1, sample_rate=1, pulse_width=3, sample_avg=2):
        """
        set up max30101; there are 2 modes: 'spo2' and 'multi' (for all 3 led's)
        
        Recommended Settings?
        Finger: LED = 4, adc_range = 3, sample_rate = 1, pulse_width = 3, sample_avg = 2
        Wrist: LED = 14, adc_range = 3, sample_rate = 1, pulse_width = 3, sample_avg = 2
        """
                
        self.bus = SMBus(BUS)
      
        # set mode
        if mode == 'spo2' or mode == 'SpO2':
            self.spo2_mode(led)
        elif mode == 'multi':
            self.multi_mode(led)
        
        # set settings for PulseOx data
        self.set_adc_range(adc_range)
        self.set_sample_rate(sample_rate)
        self.set_pulse_width(pulse_width)
        self.set_sample_avg(sample_avg)
        
        # turn on data overflow
        self.set_overflow(1)
        
    def spo2_mode(self, current):
        """
        Sets MAX30101 to SPO2 mode and turns on appropriate LED's. Current specifies desired current of LED
        """
        # reset, mainly to clear stack
        self.reset()
        
        # set mode
        mode_byte = self.bus.read_byte_data(PULSEOX_ADDR, MODE_CONFIG) & 0xFF
        mode_byte = ((mode_byte | 0x03) & 0xFB)
        self.bus.write_byte_data(PULSEOX_ADDR, MODE_CONFIG, mode_byte)
        
        # set current
        self.set_red(current)
        self.set_ir(current)
        
    def multi_mode(self, current):
        """
        Sets MAX30101 to multi-led mode (good for having all 3 led's on). Current specifies desired current of LED
        """
        # reset
        self.reset()
        
        # set mode
        mode_byte = self.bus.read_byte_data(PULSEOX_ADDR, MODE_CONFIG) & 0xFF
        mode_byte = mode_byte | 0x07
        self.bus.write_byte_data(PULSEOX_ADDR, MODE_CONFIG, mode_byte)
        
        # set config
        register1 = self.bus.read_byte_data(PULSEOX_ADDR, MULTI_MODE_1)
        register1 |= 0x21
        self.bus.write_byte_data(PULSEOX_ADDR, MULTI_MODE_1, register1)
        register2 = self.bus.read_byte_data(PULSEOX_ADDR, MULTI_MODE_2)
        register2 |= 0x03
        self.bus.write_byte_data(PULSEOX_ADDR, MULTI_MODE_2, register2)
        
        # set current
        self.set_red(current)
        self.set_ir(current)
        self.set_green(current)
        
    def is_data_ready(self):
        """
        Check if there is enough data stored in the FIFO for us to read.
        """
        write_ptr = self.bus.read_byte_data(PULSEOX_ADDR, FIFO_WR_PTR) & 0x1F
        read_ptr = self.bus.read_byte_data(PULSEOX_ADDR, FIFO_RD_PTR) & 0x1F 
        
        # number of available samples calculation needs to account for pointer wraparound
        if write_ptr >= read_ptr:
            available_samples = write_ptr - read_ptr
        else:
            # the 32 is because the FIFO stores 32 data points
            available_samples = 32 - read_ptr + write_ptr
        return (available_samples >= NUM_SAMPLES)

    def read_spo2_data(self):
        """
        Read data from FIFO with processing (ie. separating red and IR led data). Returns tuple (red data, ir data) 
        """
        # make sure we have enough data to read
        while not self.is_data_ready():
            continue

        data = self.bus.read_i2c_block_data(PULSEOX_ADDR, FIFO_DATA, SPO2_SIZE)

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
        
        return (red, ir)

    def plot_spo2_waveform(self):
        """
        Real time plot of red, ir led waveforms while in spo2 mode
        """
        # plot waveform - adapted from stackoverflow.com/questions/45046239/python-realtime-plot-using-pyqtgraph
        app = QtGui.QApplication([])
        
        win = pg.GraphicsWindow(title='PulseOx Data')
        win.resize(1000,600)
        win.setWindowTitle('Waveform Data')
        
        p1 = win.addPlot(title='Waveform Data')
        redCurve = p1.plot()
        irCurve = p1.plot()

        windowWidth = 100
        redData = np.linspace(0,0,windowWidth)
        irData = np.linspace(0,0,windowWidth)
        
        ptr = windowWidth - 1 # pointer to where data is added to our plot
        
        # enable antialiasing
        pg.setConfigOptions(antialias=True)
        
        # realtime data plotting
        while True:
            # update data
            dataPoint = self.read_spo2_data()
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

    def read_multi_data(self):
        """
        Read data from FIFO with processing (ie. separating red and IR and green led data). Returns tuple (red data, ir data, green data)
        """
        # make sure we have enough data to read
        while not self.is_data_ready():
            continue

        data = self.bus.read_i2c_block_data(PULSEOX_ADDR, FIFO_DATA, MULTI_SIZE)

        # convert ints to hex format
        data = list(map(lambda x: "0x{:02x}".format(x), data))
        # ignore the 0x prefix
        data = list(map(lambda x : x[x.index('x') + 1:], data))
        # combine bytes of data
        red = '0x' + data[0] + data[1] + data[2]
        ir = '0x' + data[3] + data[4] + data[5]
        green = '0x' + data[6] + data[7] + data[8]
        # convert back to int
        red = int(red, 0)
        ir = int(ir, 0)
        green = int(green, 0)

        return (red, ir, green)

    def plot_multi_waveform(self):
        """
        Real time plot of red, ir, green led waveforms while in multi-led mode
        """
        # plot waveform - adapted from stackoverflow.com/questions/45046239/python-realtime-plot-using-pyqtgraph
        app = QtGui.QApplication([])
        
        win = pg.GraphicsWindow(title='PulseOx Data')
        win.resize(1000,600)
        win.setWindowTitle('Waveform Data')
        
        p1 = win.addPlot(title='Waveform Data')
        redCurve = p1.plot()
        irCurve = p1.plot()
        greenCurve = p1.plot()

        windowWidth = 100
        redData = np.linspace(0,0,windowWidth)
        irData = np.linspace(0,0,windowWidth)
        greenData = np.linspace(0,0,windowWidth)
        
        ptr = windowWidth - 1 # pointer to where data is added to our plot
        
        # enable antialiasing
        pg.setConfigOptions(antialias=True)
        
        # realtime data plotting
        while True:
            # update data
            dataPoint = self.read_multi_data()
            redData[ptr] = dataPoint[0]
            irData[ptr] = dataPoint[1]
            greenData[ptr] = dataPoint[2]
            # shift data windows one to the left
            redData[:-1] = redData[1:]
            irData[:-1] = irData[1:]
            greenData[:-1] = greenData[1:]
            
            # update plot
            redCurve.setData(redData)
            irCurve.setData(irData)
            greenCurve.setData(greenData)
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
        
    def set_adc_range(self, level):
        """
        Set ADC full scale range
        
        Levels: scale parameter to full scale setting...
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
        Set sample rate
        
        Level:
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
        Set pulse width of led; indirectly influences ADC resolution as well (check datasheet)
        
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

    def set_red(self, current):
        """
        set red LED
        
        current is in mA and can must be between 0 and 51 (in mA), inclusive
        """
        if current > 51 or current < 0:
            print('Invalid Input')
            return
        led_reg = int(current / 0.2)
        self.bus.write_byte_data(PULSEOX_ADDR, LED1_PA, led_reg)

    def set_ir(self, current):
        """
        sets IR LED
        
        current is in mA and can must be between 0 and 51 (in mA), inclusive
        """
        if current > 51 or current < 0:
            print('Invalid Input')
            return
        led_reg = int(current / 0.2)
        self.bus.write_byte_data(PULSEOX_ADDR, LED2_PA, led_reg)
        
    def set_green(self, current):
        """
        sets green LED
        
        current is in mA and can must be between 0 and 51 (in mA), inclusive
        """
        if current > 51 or current < 0:
            print('Invalid Input')
            return
        led_reg = int(current / 0.2)
        self.bus.write_byte_data(PULSEOX_ADDR, LED3_PA, led_reg)

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
        
    def collect_spo2_data(self):
        time.sleep(5)
        with open(f'data_{datetime.now()}.csv', 'w') as csvfile:
            fieldnames = ['time', 'Reflect: Red', 'Reflect: IR']
            writer = csv.DictWriter(csvfile, fieldnames)
            
            writer.writeheader()    
            start_time=time.time()
            
            for i in range(200):
                refData = self.read_spo2_data()
                
                writer.writerow({fieldnames[0] : time.time() - start_time, fieldnames[1] : refData[0], fieldnames[2] : refData[1]})
            csvfile.close()
        self.reset()

### SAMPLE USAGE
#pulseOx = MAX30101(mode='spo2',led=18 , adc_range=2 , sample_rate=1, pulse_width=3, sample_avg=2)
#pulseOx.plot_spo2_waveform()
# for i in range(100):
    # data = pulseOx.read_multi_data()
    # print(data)
# pulseOx.reset()