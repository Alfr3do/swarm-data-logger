#import sys
import serial
from serial.tools import list_ports
import requests
import time

class Exo2():

	command1 = b'data\r\n'
	command2 = b'data\r'
	PARAM_COMMAND = b'para\r'
	RUN_COMMAND = b'run\r'
	GET_DATA_COMMAND = b'ssn\r'

	DUMMY = 'dummy'
	SERIAL = 'serial'
	USB = 'USB'
	API = 'API'


	PARAMS_DICT = {
	1: "Temperature (C)", # In degrees
	2: "Temperature (F)",
	3: "Temperature (K)",
	4: "Conductivity (mS/cm)",
	5: "Conductivity (uS/cm)", #u mircro S/cm
	6: "Specific Conductance (mS/cm)",
	7: "Specific Conductance (uS/cm)",
	10: "TDS (g/L)",
	12: "Salinity (PPT)",
	17: "pH (mV)",
	18: "pH",
	19: "ORP (mV)",
	20: "Pressure (psia)",
	21: "Pressure (psig)",
	22: "Depth (m)",
	23: "Depth (ft)",
	28: "Battery (V)",
	37: "Turbidity (NTU)",
	47: "NH3 (Ammonia) (mg/L)",
	48: "NH4 (Ammonium) (mg/L)",
	51: "Date (DDMMYY)",
	52: "Date (MMDDYY)",
	53: "Date (YYMMDD)",
	54: "Time (HHMMSS)",
	95: "TDS (kg/L)",
	101: "NO3 (Nitrate) (mV)",
	106: "NO3 (Nitrate) (mg/L)",
	108: "NH4 (Ammonium) (mV)",
	110: "TDS (mg/L)",
	112: "Chloride (mg/L)",
	145: "Chloride (mV)",
	190: "TSS (mg/L)",
	191: "TSS (g/L)",
	193: "Chlorophyll (ug/L)",
	194: "Chlorophyll (RFU)",
	201: "PAR (Channel 1)",
	202: "PAR (Channel 2)",
	204: "Rhodamine (ug/L)",
	211: "ODO (%Sat)",
	212: "ODO (mg/L)",
	214: "ODO (%Sat Local)",
	215: "TAL-PC (cells/mL)",
	216: "BGA-PC (RFU)",
	217: "TAL-PE (cells/mL)",
	218: "BGA-PE (RFU)",
	223: "Turbidity (FNU)",
	224: "Turbidity (Raw)",
	225: "BGA-PC (ug/L)",
	226: "BGA-PE (ug/L)",
	227: "fDOM (RFU)",
	228: "fDOM (QSU)",
	229: "Wiper Position (V)",
	230: "External Power (V)",
	231: "BGA-PC (Raw)",
	232: "BGA-PE (Raw)",
	233: "fDOM (Raw)",
	234: "Chlorophyll (Raw)",
	235: "Potassium (mV)",
	236: "Potassium (mg/L)",
	237: "nLF Conductivity (mS/cm)",
	238: "nLF Conductivity (uS/cm)",
	239: "Wiper Peak Current (mA)",
	240: "Vertical Position (m)",
	241: "Vertical Position (ft)",
	242: "Chlorophyll (cells/mL)"
	}

	def __init__(self, host='localhost', port='COM4', baudrate=9600, timeout=0.05, conn_type=SERIAL, test=False):
		## conn_type = self.[SERIAL|API|USB|DUMMY]
		super().__init__()
		self.host = host
		self.port	= port
		self.baudrate=baudrate
		self.timeout = timeout
		self.conn_type = conn_type
		if (test): self.conn_type = self.DUMMY
		print('conn type: ', self.conn_type)


		self.server_url = f"http://{self.host}:{self.port}/data"

		if (self.conn_type == self.SERIAL ):
			self.serial  = serial.Serial(
				port=self.port,
				baudrate=self.baudrate,
				bytesize=serial.EIGHTBITS,
				parity=serial.PARITY_NONE,
				stopbits=serial.STOPBITS_ONE,
				xonxoff=False,  # Disable software flow control
				rtscts=False,  # Disable hardware (RTS/CTS) flow control
				timeout=self.timeout  # Read timeout
				)
		elif (self.conn_type == self.API):
			print(self.get_data_from_command(b'init'))
		elif (self.conn_type == self.DUMMY):
			pass

	def __enter__ (self):
		return self

	def initialSetup(self, params):
		time.sleep(0.5)
		self.serial.write(b'setecho 1\r')
		command = self.serial.readline()
		data = self.serial.readline()
		print("Echo: "+data)
		self.serial.write(b'pwruptorun 0\r')
		command = self.serial.readline()
		data = self.serial.readline()
		print("No run: "+data)
		self.serial.write(b'para '+params+'\r')
		command = self.serial.readline()
		data = self.serial.readline()
		print("parameters: "+data)
	def get_active_usb_serial_ports(self):
		# Get a list of all available serial ports

		return [(device, description) for device, description, hwid in list_ports.comports() if 'USB' in description ]

	def get_data_from_command(self, command):
		"""
		Send a POST request to the server with the specified command and retrieve the data.

		Args:
			command (str): The command string to send to the exo2 sonde.

		Returns:
			str: The data received from the exo2 sensor, or None if an error occurred.
		"""
		try:
			response = requests.post(self.server_url, data=command)
			response.raise_for_status()  # Raise an exception for non-2xx status codes
			return response.text
		except requests.RequestException as e:
			print(f"Error sending command to server: {e}")
			return None

	def read_data(self):
		data_string = ""
		if (self.conn_type == self.SERIAL):
			time.sleep(0.5)
			self.serial.write(self.command2)
			time.sleep(0.5)
			command = self.serial.readline()
			data = self.serial.readline()
			data_string = data.decode('utf-8').strip()
		return data_string
	def get_data(self):
		"""
		Send a GET request to the exo2 sensor and retrieve the data.

		Returns:
			str: The data received from the exo2 sensor, or None if an error occurred.
		"""
		if (self.conn_type == self.SERIAL):
			self.serial.write(self.GET_DATA_COMMAND)
			# time.sleep(0.5)
			row = self.serial.readlines().decode()
			return row
		elif (self.conn_type == self.API):
			try:
				response = requests.get(self.server_url) # Uses a get request instead of using send_command('data') for performance reasons
				response.raise_for_status()  # Raise an exception for non-2xx status codes
				return response.text
			except requests.RequestException as e:
				print(f"Error fetching data from server: {e}")
				return None
		elif (self.conn_type == self.DUMMY):
			return '30,8'

	def get_exo2_data(self):
		"""
		Get data from the Exo2 sensor.

		Returns:
			list: A list of float values representing the data from the Exo2 sensor.
		"""

		exo2_data_str = self.get_data()
		while not exo2_data_str or "#" in exo2_data_str:
			# Keep requesting data until a non-empty string (other than "#") is received
			exo2_data_str = self.get_data()

		# Split the received string on whitespace and convert values to floats
		
		exo2_data_list = exo2_data_str.split()
		assert len(exo2_data_list) == len(self.exo2_params), 'For some reason the params and the data size do not match'
		exo2_data_dict = { param_name : float(value) for param_name, value in zip(self.exo2_params.values(), exo2_data_list) }
		return exo2_data_dict

	def get_exo2_params(self):
		"""
		Get the Exo2 sensor parameters by sending the 'para' command.

		Returns:
			str: The parameters received from the server, or None if an error occurred.
		"""
		if (self.conn_type == self.SERIAL):
			time.sleep(0.5)
			self.serial.write(self.PARAM_COMMAND)
			time.sleep(0.5)
			command = self.serial.readline()
			data = self.serial.readline()
			data_string = data.decode('utf-8').strip()
			param_list = data_string.split()
			param_name_list = [self.PARAMS_DICT[int(x)] for x in param_list]
			
			return param_list, param_name_list

		elif(self.conn_type == self.API):
			param_str = self.get_data_from_command('para')
			while not param_str or "#" in param_str:
				# Keep requesting data until a non-empty string (other than "#") is received
				param_str = self.get_data_from_command('para')

			# Split the received string on whitespace and convert values to ints
			param_list = list(map(int, param_str.split()))
			print(param_list)
		elif (self.conn_type == self.DUMMY):
			param_list = [1,4]
		return {key : self.PARAMS_DICT[key] for key in param_list}

	def start_collection(self):
		#TODO: test if the encode is needed
		self.serial.write(self.RUN_COMMAND.encode())

	def __exit__(self, *args):
		if (self.conn_type == self.SERIAL):
			self.serial.close()
