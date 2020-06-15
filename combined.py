from MAX30101 import *
from CMS50D import *

def main():
    refPulseOx = MAX30101()
    transPulseOx = CMS50D('/dev/ttyUSB0')
    
    # plot waveform - adapted from stackoverflow.com/questions/45046239/python-realtime-plot-using-pyqtgraph
    app = QtGui.QApplication([])

    win = pg.GraphicsWindow(title='PulseOx Data')
    win.resize(1000,600)
    win.setWindowTitle('Waveform Data')

    p1 = win.addPlot(title='Waveform Data')
    transCurve = p1.plot()
    reflectRedCurve = p1.plot()
    reflectIrCurve = p1.plot()
    # p1.setRange(yRange=(0,100))
    windowWidth = 500
    transData = np.linspace(0,0,windowWidth)
    refRedData = np.linspace(0,0,windowWidth)
    refIrData = np.linspace(0,0,windowWidth)

    ptr = windowWidth - 1 # pointer to where data is added to our plot
    
    # enable antialiasing
    pg.setConfigOptions(antialias=True)

    # realtime data plotting
    for i in range(10000):
        # update data
        transData[ptr] = transPulseOx.get_waveform_data()

        # since refPulseOx data collection fluctuates a lot, only take data above a certain threshold
        refRedDataPoint = 0
        refIrDataPoint = 0
        while refRedDataPoint < 3000: 
            refRedDataPoint, refIrDataPoint = refPulseOx.read_data()
        refRedData[ptr] = refRedDataPoint
        refIrData[ptr] = refIrDataPoint

        # shift data windows one to the left
        transData[:-1] = data[1:]
        refRedData[:-1] = data[1:]
        refIrData[:-1] = data[1:]
        
        # update plot
        transCurve.setData(transData)
        refRedCurve.setData(refRedData)
        refIrCurve.setData(refIrData)
        QtGui.QApplication.processEvents()

    # close Qt
    pg.QtGui.QApplication.processEvents()

if __name__ == "__main__":
    main()
