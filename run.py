import time
import surveyor

from exo2 import Exo2
import datetime
from pymongo import MongoClient
import certifi
import sys
import os
import geopy.distance
import json
from watersampler import WaterSamplerController

current_coordinates = None

CONNECTION_AWS = os.environ['COSMODB_STRING']
client = MongoClient(CONNECTION_AWS, tlsCAFile=certifi.where())

keys = []
#port = 'COM4'
port = '/dev/ttyUSB0'
baudrate = 9600
take_samples = False
sample_points = []
MIN_DIST = 0.005


def read_sensor_data(sensor, coordinates=(0,0), asvid=0):
    global keys
    data_string = sensor.read_data()
    #print("Data",data_string)
    data_list = data_string.split()
    # print(len(data_list))
    if len(data_list) > 1:
        #keys = ['Date', 'Time', 'Chl (ug/L)', 'BGA-PE (ug/L)', 'Turb (FNU)', 'TSS (mg/L)', 'ODO (%sat)', 'ODO (mg/l)', 'Temp (C)', 'Cond (uS/cm)', 'Sal (PPT)', 'Pressure (psi a)', 'Depth (m)']
        if len(keys) != len(data_list):
            keys, _ = sensor.get_exo2_params()
        data_dict = {}
        data_dict_exo = {keys[i]: data_list[i] for i in range(len(keys))}
        data_dict['exodata'] = data_dict_exo 
        data_dict['date'] = datetime.datetime.now().strftime("%Y-%m-%d")
        data_dict['time'] = datetime.datetime.now().strftime("%H:%M:%S")
        data_dict['latitude'] = current_coordinates[0]
        data_dict['longitude'] = current_coordinates[1]
        data_dict['timestamp'] = datetime.datetime.now()
        data_dict['metadata'] = {}
        data_dict['metadata']['asvid'] = asvid
        data_dict['metadata']['sn'] = sensor.get_sn()
        data_dict['metadata']['ssn'] = sensor.get_ssn()
        return data_dict
    else:
        pass

def save_data_to_db(collection_name='test', data={}):
    # client = MongoClient(CONNECTION_STRING)
    #print(f"DB Client: {client}")
    db = client.missions
    #print(f"DB: {db}")

    collection = db[collection_name]
    if data:
        collection.insert_one(data)
        print('Data saved: ', data)

def save_data_to_file(file, data={}):
    
    if data:
        file.write(json.dumps(data,default=str))
        file.flush()
def take_sample(pos, sampler, filename,data):
    data = json.dumps(data,default=str)
    print("taking sample at ", pos, data)
    sampler.sample_and_log(filename, data, updated_coords=pos)

if __name__ == "__main__":
    asvid = 0
    mission_name = datetime.datetime.now().strftime("%Y%m%d%H%M")
    sample_output = mission_name+"-samples.txt"
    print(sys.argv)

    if len(sys.argv) <= 1 :
        print("*** ATENTION *** python run.py [id] [mission_name] [sample_points_file] [samples_ouput], to save the ASV id, and name the mission")
    if len(sys.argv) > 1 :
        asvid = sys.argv[1]
    if len(sys.argv) > 2 :
        mission_name = sys.argv[2]
    
    if len(sys.argv) > 3 :
        sample_points_file = sys.argv[3]
        take_samples = True
        with open(sample_points_file, 'r+') as f:
            for line in f:
                point = line.strip().split(",")
                print(point)
                sample_points.append((float(point[0]),float(point[1])))
    if len(sys.argv) > 4 :
        sample_output = sys.argv[4]
    try:
        sampler = WaterSamplerController()
        collection_name = '' + mission_name
        instant_fault = True
        keys = []
        while (instant_fault):
            try:
                exo = Exo2('localhost', port, 9600, 0.05, Exo2.SERIAL)
                #exo.initial_setup('1 5 12 20 22 53 54 211 212')
                keys, _ = exo.get_exo2_params()
                print("keys ",keys)
                if len(keys) > 0:
                    instant_fault = False
            except Exception as ex:
                print("not successful ",ex)
                sys.exit()
                pass
            
        with surveyor.Surveyor(dummy=False) as s, open(collection_name+".csv", "w") as file:
            print("running surveyor")
            for i in range(1000):
                try:
                    current_coordinates = s.get_gps_coordinates()
                    #print("here ", current_coordinates)
                    #current_time = s.get_timestamp()
                    print(current_coordinates)
                    if (current_coordinates and current_coordinates[0] != 0):
                        
                        data = read_sensor_data(exo, current_coordinates, asvid)

                        if (take_samples):
                            for i in range(len(sample_points)):
                                distance = geopy.distance.geodesic(sample_points[i], current_coordinates)
                                print(f"distance to {i} is {distance}")
                                if distance < MIN_DIST:
                                    sample_points.remove(sample_points[i])
                                    take_sample(current_coordinates, sampler, sample_output,data)
                                    break
                                    
                        save_data_to_db(data=data, collection_name=collection_name)
                        save_data_to_file(file, data)
                        print(data)
                except Exception as exception:
                    print(exception)
                
                time.sleep(0.2)
    except Exception as exception:
        print(exception)
    finally:
        exo.close()
        client.close()

    # ser.close()
    print("Close the serial connection")
        # hlp.save(current_coordinates, exo2_data, add_noise)
