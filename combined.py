from MAX30101 import *
from CMS50D import *
import csv
import time

def real_time_plot():    
    # plot waveform - adapted from stackoverflow.com/questions/45046239/python-realtime-plot-using-pyqtgraph
    app = QtGui.QApplication([])

    win = pg.GraphicsWindow(title='PulseOx Data')
    win.resize(1000,600)
    win.setWindowTitle('Waveform Data')

    p1 = win.addPlot(title='Waveform Data')
    transCurve = p1.plot()
    refRedCurve = p1.plot()
    refIrCurve = p1.plot()
    # p1.setRange(yRange=(0,100))
    windowWidth = 500
    transData = np.linspace(0,0,windowWidth)
    refRedData = np.linspace(0,0,windowWidth)
    refIrData = np.linspace(0,0,windowWidth)

    ptr = windowWidth - 1 # pointer to where data is added to our plot
    
    # enable antialiasing
    pg.setConfigOptions(antialias=True)

    # initialize data collection
    refPulseOx = MAX30101()
    transPulseOx = CMS50D('/dev/ttyUSB0')

    # realtime data plotting
    while True:
        # update data
        transData[ptr] = transPulseOx.get_waveform_data()

        # since refPulseOx data collection fluctuates a lot, only take data above a certain threshold
        refRedDataPoint = 0
        refIrDataPoint = 0
    #    while refRedDataPoint < 3000: 
        refDataPoint = refPulseOx.read_data()
        print(refDataPoint)
        refRedData[ptr] = max(0, refDataPoint[0] - 20600)
        refIrData[ptr] = max(0, refDataPoint[1] - 20600)
        # shift data windows one to the left
        transData[:-1] = transData[1:]
        refRedData[:-1] = refRedData[1:]
        refIrData[:-1] = refIrData[1:]
        
        # update plot
        transCurve.setData(transData)
        refRedCurve.setData(refRedData)
        refIrCurve.setData(refIrData)
        QtGui.QApplication.processEvents()

    # close Qt
    pg.QtGui.QApplication.exec_()

def collect_data():
    transPulseOx = CMS50D('/dev/ttyUSB0')

    time.sleep(5)

    with open('data.csv', 'w') as csvfile:
        fieldnames = ['Transmission', 'Reflection: Red', 'Reflection: IR']
        writer = csv.DictWriter(csvfile, fieldnames)
        
        writer.writeheader()    
        refPulseOx = MAX30101()
        transPulseOx = CMS50D('/dev/ttyUSB0')

        for i in range(1000):
            transData = transPulseOx.get_waveform_data()
            refData = refPulseOx.read_data()
            
            writer.writerow({fieldnames[0] : transData, fieldnames[1] : refData[0], fieldnames[2] : refData[1]})
            time.sleep(0.03)
        csvfile.close()
            
collect_data()
