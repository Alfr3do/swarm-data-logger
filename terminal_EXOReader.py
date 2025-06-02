import serial
import time
from datetime import datetime, timedelta

def main():
    port = '/dev/ttyUSB1'
    baudrate = 9600

    ser = serial.Serial(port, baudrate, timeout = 1)
    time.sleep(1)
    try:
        while True:
            count = 0
            command = input('Command: ').encode('UTF-8')
            ser.write(command + b'\r')
            response = ser.readline().decode('UTF-8')
            print(f'Response: {response}')
            response = ser.readline().decode()
            print(f'Response: {response}')
            #while not response and count <5: #and not str(command) in str(response):
            #    response = ser.readline().decode()
            #    print(f'Response: {response}')
            #    count += 1
    except KeyboardInterrupt:
        print('Program terminated by the user.')
    finally:
        ser.close()

if __name__ == '__main__':
    main()
