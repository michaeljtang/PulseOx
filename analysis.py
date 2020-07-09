from MAX30101 import *

def change_led():
	for i in range(6, 21, 2):
		pulseOx = MAX30101(mode='spo2',led=i , adc_range=3 , sample_rate=1, pulse_width=3, sample_avg=2)
		pulseOx.collect_spo2_data()

def change_adc():
	for i in range(1,4):
		pulseOx = MAX30101(mode='spo2',led=18 , adc_range=i , sample_rate=1, pulse_width=3, sample_avg=2)
		pulseOx.collect_spo2_data()

def change_pulse():
	for i in range(4):
		pulseOx = MAX30101(mode='spo2',led=18 , adc_range=2 , sample_rate=1, pulse_width=i, sample_avg=2)
		pulseOx.collect_spo2_data()

change_pulse()
