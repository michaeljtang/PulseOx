import serial
import array
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import time

class CMS50D(object):
    """
    Object for CMS50D PulseOx
    """
    #TODO: Properly decode "finger out" flag, assuming it exists
    def __init__(self, portstr):
        """
        portstr: address of device connection. On RPi, this is "/dev/ttyUSB0"
        """
        self.port = serial.Serial(portstr, 115200, timeout=0.01, stopbits=serial.STOPBITS_ONE, parity=serial.PARITY_NONE, bytesize=serial.EIGHTBITS, xonxoff=1)
        # handshake to tell pulseOx to start transmitting data
        self.port.write(b'\x7d\x81\xa1\x80\x80\x80\x80\x80\x80')      

    def get_data(self):
        """
        Returns tuple (bpm, spo2, waveform data)
        """
        raw = []
        tries = 0
        while(len(raw) < 9):
            # code sends data in chunks of 9
            raw = self.port.read(9)

            tries += 1
            # if we try too many times without getting data, resend handshake
            if tries >= 3:
                self.port.write(b'\x7d\x81\xa1\x80\x80\x80\x80\x80\x80')      
        
        # get bits 0-6 of byte 3
        return (raw[5] & 0x7f, raw[6] & 0x7f, raw[3] & 0x7f)

    def get_waveform_data(self):
        """
        Returns a single point of pulse waveform data (an int)
        """
        raw = []
        tries = 0
        while(len(raw) < 9):
            raw = self.port.read(9)

            tries += 1
            # if we try too many times without getting data, resend handshake
            if tries >= 3:
                self.port.write(b'\x7d\x81\xa1\x80\x80\x80\x80\x80\x80')      
        
        return raw[3] & 0x7f
        
    def plot_waveform(self):
        """
        adapted from: stackoverflow.com/questions/45046239/python-realtime-plot-using-pyqtgraph
        Gives real-time PPG plot
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
       
    def close(self):
        self.port.close()


### Example Usage
# pulseOx=CMS50D("/dev/ttyUSB0")
# while True:
    # data=pulseOx.get_data()
    # print(data)