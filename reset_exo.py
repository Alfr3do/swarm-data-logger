from exo2 import Exo2

port = '/dev/ttyUSB5'

exo = Exo2('',port,9600,0.05,Exo2.SERIAL)

exo.serial.write(b'0')
exo.serial.readline()
exo.serial.readline()
exo.serial.readline()
res = b''
while not res:
	exo.serial.write(b'setecho\r')
	res = exo.serial.readline()
print(res)
if res == b'?Command\r\n':
	res = exo.serial.readline()
if res == b'setecho\r\n':
	#echo is on just received echo
	#read response
	echo = exo.serial.readline()
	#read hashtagb
	exo.serial.readline()
if res == b'0':
	#echo is off 
	#turn it back on

	exo.serial.write(b'setecho 1\r')
	res = exo.serial.readline()
	print(res)
	exo.serial.readline()
	exo.serial.readline()


