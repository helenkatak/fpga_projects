import numpy as np
import serial
import time
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.multiprocess as mp
import threading
from PIL import Image


class EventPlotter(object):
	def __init__(self, ser):
		self.app = pg.mkQApp()
		self.proc = mp.QtProcess()
		self.rpg = self.proc._import('pyqtgraph')
				
		self.plotwin = self.rpg.GraphicsWindow(title="Monitor")
		self.plotwin.resize(800,500)
		self.plotwin.setWindowTitle('Activity Monitor')
		self.p1 = self.plotwin.addPlot(title="Neuron spikes vs. time")
		self.p1.setLabel('left', 'Neuron Id')
		self.p1.setLabel('bottom', 'Time [s]')
		self.p1.showGrid(x=True, y=True, alpha=0.5)
		self.spikes_curve = self.p1.plot(pen=None, symbol="o", symbolPen=None, symbolBrush='w', symbolSize=3)   
		# self.app.exit(self.app.exec_()) # not sure if this is necessary	
		self.on_screen = 200 # Number of events on the screen
		self.all_time_stamps = np.zeros(self.on_screen)
		self.all_addresses = np.zeros(self.on_screen, dtype=int)
		
		self.ser = ser
		self.old_stamp = 0

	def decode_events(self, byte_data):
		time_stamps = []
		addresses = []
		event_nr = int(len(byte_data)/3)
		
		if event_nr > 0:
			for e in range(event_nr):
				event = byte_data[e*3:e*3+3]
				addresses.append(event[2])
				new_stamp = int.from_bytes(event[0:2], byteorder='big')
				time_stamps.append(new_stamp)
				
		return time_stamps, addresses

	def ReadEvents(self):
		try:
			event_data = self.ser.read(300)
			time_stamps, addresses = self.decode_events(event_data)
			dn = len(time_stamps)
			if dn > 0:
				self.all_time_stamps = np.roll(self.all_time_stamps, -dn)
				self.all_addresses = np.roll(self.all_addresses, -dn)
				self.all_time_stamps[-dn:] = np.array(time_stamps)
				self.all_addresses[-dn:] = np.array(addresses)				
				self.spikes_curve.setData(x=self.all_time_stamps, y=self.all_addresses, _callSync='off')
		except:
			None
            
def go_function():
    ser.write((int(10)).to_bytes(1, byteorder="little"))
    time.sleep(0.001)  
    
    while True:
        data_bytes = ser.read(3)
        if (data_bytes != b''):
            split = [data_bytes[i] for i in range (0,len(data_bytes))]
            data_list = [split[0]*(2^8)+split[1], split[2]]
            print(data_list)
            
# Seial port initialization 
ser = serial.Serial()
ser.baudrate = 115200
ser.port = 'COM5'
ser.timeout = 0.1
ser.open()
# Flags
script_on = True 
spikes_on = False
EventPlotter = EventPlotter(ser=ser)

def cmd_in():  
    global script_on, spikes_on, EventPlotter     
    while True:
        cmd_raw = input("Enter a command quit/show/clear/pause/read/write => ").split()
        cmd_line = cmd_raw[0] 
        if (len(cmd_raw) == 2):                 
            cmd_param = int(cmd_raw[1])
        elif (len(cmd_raw) == 4):
            cmd_addr = int(cmd_raw[1])
            cmd_activity = int(cmd_raw[2])       # string
            cmd_value = int(cmd_raw[3])
        else:
            cmd_param = 0   
            cmd_addr = 0
            cmd_value = 0
            cmd_activity = 0
                          
        if (cmd_line == "show"):
            ser.write(bytes.fromhex('01'))              # Decimal 01
            time.sleep(0.001)
            try:
                EventPlotter.on_screen = cmd_param           
                EventPlotter.all_time_stamps = np.zeros(EventPlotter.on_screen)
                EventPlotter.all_addresses = np.zeros(EventPlotter.on_screen, dtype=int)
            except:
                print("Invalid number after show command.\n")
   
        elif (cmd_line == "go"):
            if (spikes_on == False):
                ser.write(bytes.fromhex('01'))
                spikes_on = True
            EventPlotter.on_screen = cmd_param
             
        elif (cmd_line == "quit"):    # quit the python code
            ser.write(bytes.fromhex('00'))              # Decimal 11
            script_on = False
            ser.close()
            break
                
        elif (cmd_line == "stop"):
            ser.write(bytes.fromhex('00'))
            spikes_on = False
        
        elif (cmd_line == "read"):
            ser.write(bytes.fromhex('03'))                          # enable ext read
            ser.write(cmd_param.to_bytes(1, byteorder="little")[1]) # Read address
            data_bytes = ser.read(2)                                # 13 bit
            print(data_bytes)        

        elif (cmd_line == "write"):           
            ser.write(bytes.fromhex('02'))                              # enable ext write
            ser.write(cmd_addr.to_bytes(1, byteorder="little"))      # send address
            ser.write(cmd_activity.to_bytes(2, byteorder="little")[1])  # send 1st 1byte of activity
            ser.write(cmd_activity.to_bytes(2, byteorder="little")[0])  # send 2nd 1byte of activity
            ser.write(cmd_value.to_bytes(1, byteorder="little")) 
         
        elif (cmd_line == "clear"):
            ser.write(bytes.fromhex('05'))
            EventPlotter.all_time_stamps = np.zeros(EventPlotter.on_screen)
            EventPlotter.all_addresses = np.zeros(EventPlotter.on_screen, dtype = int)
            

# thread_img = threading.Thread(target=run_img)
# thread_img.daemon = False
# thread_img.start()

def run_plot():
	global script_on, EventPlotter, spikes_on
	while script_on == True:
		time.sleep(100e-3)
		EventPlotter.ReadEvents()
	EventPlotter.proc.close()

thread_plot = threading.Thread(target=run_plot)
thread_plot.daemon = False
thread_plot.start()

cmd_in()