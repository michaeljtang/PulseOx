import serial
import array
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import time

class CMS50D(object):
    #TODO: Properly decode "finger out" flag, assuming it exists
    def __init__(self, portstr):
        self.port = serial.Serial(portstr, 115200, timeout=0.01, stopbits=serial.STOPBITS_ONE, parity=serial.PARITY_NONE, bytesize=serial.EIGHTBITS, xonxoff=1)
        self.current_bpm = None
        self.current_spo2 = None
        self.port.write(b'\x7d\x81\xa1\x80\x80\x80\x80\x80\x80')      

    def get_data(self):
        """
        Returns bpm, spo2, waveform data

        """
        raw = []
        while(len(raw) < 9):
            raw = self.port.read(9)
        
        # get bits 0-6 of byte 3
        return (raw[5] & 0x7f, raw[6] & 0x7f, raw[3] & 0x7f)

    def get_waveform_data(self):
        """
        Returns a single point of pulse waveform data
        """
        raw = []
        while(len(raw) < 9):
            raw = self.port.read(9)
        
        return raw[3] & 0x7f
        
    def plot_waveform(self):
        """
        code adapted from python3 -m pyqtgraph.examples Plotting.py
        also adapted from: stackoverflow.com/questions/45046239/python-realtime-plot-using-pyqtgraph
        """
        
        # initializing Qt app
        app = QtGui.QApplication([])
        
        win = pg.GraphicsWindow(title="Transmission PulseOx Data")
        win.resize(1000, 600)
        win.setWindowTitle('Waveform Data')
        
        p1 = win.addPlot(title='Waveform Data')
        curve = p1.plot()
        p1.setRange(yRange=(0, 100))
        windowWidth = 500
        data = np.linspace(0, 0, windowWidth)
        
        ptr = windowWidth - 1 # pointer to first data point
        
        # enable antialiasing
        pg.setConfigOptions(antialias=True)
        
        # realtime data plotting
        while True:
            # update data
            data[ptr] = self.get_waveform_data()
            
            # shift entire window to left
            data[:-1] = data[1:]
            
            # update plot
            curve.setData(data)
            QtGui.QApplication.processEvents()
        
        # closes Qt
        pg.QtGui.QApplication.exec_()

    def new_data_test(self):
        """
        For newer pulseOx version - tests various parameters, retrieves
        spo2 and heart rate data
        """
        raw = list(self.port.read(9))
        
        # testing ... 
        string = ''
        for i in range (9):
            string += str(raw[i] & 0x7f) + ', '
        
        print(string)
        
        ###
        spo2 = raw[6] & 0x7f
        hr = raw[5] & 0x7f
        
        # find spo2 and heart rate parameters
        for x in range(10):
#           print( raw[5] & 0x, raw[6])
            raw = self.port.read(9)
            # raw[6] & 0x7F gives heart rate correctly
            # raw[7] & 0x7F gives SPO2        
        
    def close(self):
        self.port.close()


# pulseOx=CMS50D("/dev/ttyUSB0")

# while True:
    # data=pulseOx.get_data()
    # print(data)
