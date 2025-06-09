from smbus import SMBus
import datetime
import time
import math
import tkinter as tk
from tkinter import filedialog
import shutil
import os

class WaterSamplerController():
    def __init__(self, i2c_bus=1, device_address=0x20):
        #self.bus = SMBus(i2c_bus)
        #self.address = device_address
        
        #Configure all pins (PORTA and PORTB) as outputs (0x00)
        #self.bus.write_byte_data(self.address, 0x06, 0x00) # IODIRA -> all outputs
        #self.bus.write_byte_data(self.address, 0x07, 0x00) # IODIRB -> all outputs
        
        try:
            self.bus = SMBus(i2c_bus)
            self.address = device_address
            #Configure all pins (PORTA and PORTB) as outputs (0x00)
            self.bus.write_byte_data(self.address, 0x06, 0x00) # IODIRA -> all outputs
            self.bus.write_byte_data(self.address, 0x07, 0x00) # IODIRB -> all outputs
        except OSError as e:
            print(f"Failed to initialize I2C device at address {hex(self.address)}: {e}")
            print('Check I2C connections to the RPi')
            exit(1)
        
        # List of (byte_A, byte_B) values for each motor
        self.motors = [
            (0x01, 0x00), # Motor 1 (A0)
            (0x02, 0x00), # Motor 2 (A1)
            (0x04, 0x00), # Motor 3 (A2)
            (0x08, 0x00), # Motor 4 (A3)
            (0x10, 0x00), # Motor 5 (A4)
            (0x00, 0x01), # Motor 6 (B0)
            (0x00, 0x02), # Motor 7 (B1)
            (0x00, 0x04), # Motor 8 (B2)
            (0x00, 0x08), # Motor 9 (B3)
            (0x00, 0x10), # Motor 10 (B4)
        ]
        self.current_motor_index = -1 # Start with no motor activated
        self.samplingtime = 10          #Time it takes to take a sample
        self.timebetweensamples = 300   #Time between samples when seuqnatial sampling is chosen
        self.threshold_meters = 5   #Distance between refrence and coordinate for taking a sample [m]
        
    def activate_next_motor(self, duration=None):
        self.current_motor_index += 1
        if duration==None:
            duration= self.samplingtine
        
        if self.current_motor_index >= len(self.motors):
            print("All motors have been activated.")
            return
            
        self._activate_motor(self.current_motor_index, duration)
        
    def activate_motor(self, motor_number, duration):
        if not (1 <= motor_number <= len(self.motors)):
            raise ValueError(f"Motor number must be between 1 and {len(self.motors)}")
        
        index = motor_number - 1
        self._activate_motor(index, duration)
            
    def _activate_motor(self, index, duration):
        
        byte_a, byte_b = self.motors[index]
        
        # Send data to PORTA and PORTB separately
        self.bus.write_byte_data(self.address, 0x02, byte_a) # Write to GPIOA
        self.bus.write_byte_data(self.address, 0x03, byte_b) # Write to GPIOB
        
        print(f"Motor {index + 1} activated.")
        
        # Wait for the specified duration
        time.sleep(duration)
        
        # Deactivate all motors
        self.bus.write_byte_data(self.address, 0x02, 0x00) # Clear GPIOA
        self.bus.write_byte_data(self.address, 0x03, 0x00) # Clear GPIOB
        
        print(f"Motor {index + 1} deactivated after {duration} seconds.")
        
    def stop(self):
        self.bus.write_byte_data(self.address, 0x02, 0x00) # Clear GPIOA
        self.bus.write_byte_data(self.address, 0x03, 0x00) # Clear GPIOB
        print(f"All Motors  deactivated.")
        
    def __exit__(self, *args):
        self.bus.write_byte_data(self.address, 0x02, 0x00) # Clear GPIOA
        self.bus.write_byte_data(self.address, 0x03, 0x00) # Clear GPIOB
        print(f"All Motors  deactivated.")
        

    def reset_motors(self):
        self.current_motor_index = -1
        print("Motor index reset.")
     
    def save_txt(self, motor_index, motor_state, file_name='data.txt', log_file='log.txt'):
        time_now = datetime.datetime.now()
        
        #with open(file_name, 'a') as f:
        #    f.write(f"{time_now}, {motor_index}\n")
        #print(f"{time_now}, {motor_index}")
        
        # Log instead of print to avoid stdout error
        with open(log_file, 'a') as log:
            log.write(f"{time_now}, {motor_index}, {motor_state}\n")
        print(f"{time_now}, {motor_index}")
            
    def haversine(self, coord1, coord2):
        R = 6371.0  # Earth radius in kilometers
        lat1, lon1 = coord1
        lat2, lon2 = coord2

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = math.sin(dlat / 2)**2 + \
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.sin(dlon / 2)**2

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def read_coordinates_from_file(self, filename):
        coords = []
        with open(filename, 'r') as file:
            for line in file:
                #print(line)
                line = line.strip()
                if line:  # ignore empty lines
                    parts = line.split(',')
                    if len(parts) == 2:
                        try:
                            lat = float(parts[0].strip())
                            lon = float(parts[1].strip())
                            coords.append((lat, lon))
                        except ValueError:
                            print(f"Skipping invalid line: {line}")
        return coords

    def write_coordinates_to_file(self, filename, coords):
        with open(filename, 'w') as file:
            for lat, lon in coords:
                file.write(f"{lat},{lon}\n")

    def check_and_remove_closest(self, reference_coord, coord_list):
        if not coord_list:
            return 0, coord_list

        distances = [self.haversine(reference_coord, coord) for coord in coord_list]
        min_index = distances.index(min(distances))
        min_distance = distances[min_index]

        if min_distance < (self.threshold_meters / 1000.0):
            take_sample = 1
            # Remove the closest coordinate
            coord_list.pop(min_index)
        else:
            take_sample = 0
        return take_sample, coord_list

    def browse_file(self):
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        file_path = filedialog.askopenfilename(
            title="Select GPS Coordinates File for water sampling",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        return file_path
    
    def make_backup(self, file_path):
        base, ext = os.path.splitext(file_path)
        backup_path = f"{base}_backup{ext}"
        shutil.copy(file_path, backup_path)
        print(f"Backup created: {backup_path}")
        return backup_path
    
    def sample_sequentially(self):
        print("Sequential samplig activated")
        for _ in range(10):
            #input()
            time.sleep(self.timebetweensamples)
            self.save_txt(motor_index=self.current_motor_index + 2, motor_state=1)
            self.activate_next_motor(duration=self.samplingtime)
            self.save_txt(motor_index=self.current_motor_index + 1, motor_state=0)
            
    def sample_and_log (self, filename, add_data="", updated_coords=(0,0)):
        self.save_txt(log_file=filename, motor_index=self.current_motor_index + 2, motor_state=1)
        self.save_txt(log_file=filename, motor_index=self.current_motor_index + 2, motor_state="exo: "+add_data)
        self.activate_next_motor(duration=self.samplingtime)
        self.save_txt(log_file=filename, motor_index=self.current_motor_index + 1, motor_state=0)
        self.save_txt(log_file=filename, motor_index=self.current_motor_index + 2, motor_state=f"coords: {updated_coords}")
        print(updated_coords)
        print("Sample taken")
            
    def sample_from_gps(self, filename, reference):
        coords = self.read_coordinates_from_file(filename)   #Read coordinates
        if coords:
            #print(coords)
            print(f"\nProcessing reference: {reference}")
            take_sample, updated_coords = self.check_and_remove_closest(reference, coords) #Take sample and update coordinates' list
            if take_sample:
                #self.save_txt(seld.current_motor_index + 2, motor_state=1)
                #self.activate_next_motor(duration=self.samplingtime)
                #self.save_txt(self.current_motor_index + 1, motor_state=0)
                #self.write_coordinates_to_file(filename, updated_coords)
                #print("take sample =", take_sample)
                #print(updated_coords)
                #print("Sample taken")
                sample_and_log (filename=filename)
            #else:
            #    print("Reference NOT FOUND in sampling coordinates")
        else:
            print("No valid coordinates found")

 
# Main logic
# -----------------------

if __name__ == "__main__":
    watersampler = WaterSamplerController()
    
    #Sample sequentially
    #watersampler.sample_sequentially()
    
    #watersampler.reset_motors()
    
    #Sample from GPS references. This should be provided by the ASV GPS
    reference = [
        (40.7128, -74.0060),
        (25.91067910, -80.13620540),
        (0, 0),
        (25.91109570, -80.13651560),
        (0, 0),
        (25.91125130, -80.13699580),
        (0, 0),
        (25.91168070, -80.13690590),
        (25.91182060, -80.13731900),
        (25.91235860, -80.13746380),
        (25.91278810, -80.13776150),
        (0, 0),
        (25.91317530, -80.13798950),
        (25.91354440, -80.13835030)
    ]
    
    # Let user select the file where sampling gps coordinates are
    filename = watersampler.browse_file()
    if filename:
    #filename = input("Enter the file where the sampling GPS coordinates are: ).strip()
    #filename = "/Users/croa/Desktop/FDEPMissions/coordinates.txt"
        watersampler.make_backup(filename)  # Create backup before modifying
        #Loop to simulate ASV GPS data
        for ref in reference:
            watersampler.sample_from_gps(filename=filename, reference=ref)
            time.sleep(5)
    else:
        print("No file selected")
        
        
