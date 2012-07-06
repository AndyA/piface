from array import array
import threading
import socket
import time
import sys
import struct

from Tkinter import Tk
from tkSimpleDialog import askstring
root = Tk()
root.withdraw()

PORT = 42001
HOST = '130.88.194.67'
#HOST = askstring('Scratch Connector', 'IP:')
BUFFER_SIZE = 100

SCRATCH_SENSOR_NAME_INPUT = (
	'piface-input1',
	'piface-input2',
	'piface-input3',
	'piface-input4',
	'piface-input5',
	'piface-input6',
	'piface-input7',
	'piface-input8')

SCRATCH_SENSOR_NAME_OUTPUT = (
	'piface-output1',
	'piface-output2',
	'piface-output3',
	'piface-output4',
	'piface-output5',
	'piface-output6',
	'piface-output7',
	'piface-output8')


class ScratchSender(threading.Thread):
	def __init__(self, socket):
		threading.Thread.__init__(self)
		self.scratch_socket = socket

	def run(self):
		last_bit_pattern = 0
		while True:
			pin_bit_pattern = pfio.read_input()

			# if there is a change in the input pins
			changed_pins = pin_bit_pattern ^ last_bit_pattern
			if changed_pins:
				try:
					broadcast_pin_update(changed_pins, pin_bit_pattern)
				except:
					break

			last_bit_pattern = pin_bit_pattern

	def broadcast_pin_update(self, changed_pin_map, pin_value_map):
		for i in range(8):
			# if we care about this pin's value
			if (changed_pin_map >> i) & 0b1:
				pin_value = (pin_value_map >> i) & 0b1

				bcast_str = 'sensor-update "%s" %d' % \ 
					(SCRATCH_SENSOR_NAME_INPUT[i], pin_value)

				print 'sending: %s' % bcast_str
				self.send_scratch_command(bcast_str)

	def send_scratch_command(self, cmd):
		n = len(cmd)
		a = array('c')
		a.append(chr((n >> 24) & 0xFF))
		a.append(chr((n >> 16) & 0xFF))
		a.append(chr((n >>  8) & 0xFF))
		a.append(chr(n & 0xFF))
		self.scratch_socket.send(a.tostring() + cmd)

class ScratchListener(threading.Thread):
	def __init__(self, socket):
		threading.Thread.__init__(self)
		self.scratch_socket = socket

	def run(self):
		while True:
			try:
				data = self.scratch_socket.recv(BUFFER_SIZE)
				length = struct.unpack(
						'>i',
						'%c%c%c%c' % (data[0], data[1], data[2], data[3])
					)[0]
			except: # TODO: specify and error here
				break

			#print 'Length: %d, Data: %s' % (length, data[4:])
			data = data[4:].split(" ")
			if data[0] == 'sensor-update':
				#print 'updating %s, new value: %s' % (data[1].strip('"'), data[2])
				sensor_name = data[1]
				if sensor_name in SCRATCH_SENSOR_NAME_OUTPUT:
					pin_index = SCRATCH_SENSOR_NAME_OUTPUT.index(sensor_name)+1
					if data[2] > 0:
						pfio.digital_write(pin_index, 1)
					else:
						pfio.digital_write(pin_index, 0)

			elif data[0] == 'broadcast':
				print 'received broadcast: %s' % data[1]

			else:
				print 'received something: %s' % data


def create_socket(host, port):
	scratch_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	scratch_sock.connect((host, port))
	return scratch_sock

if __name__ == '__main__':
	if not HOST:
		sys.exit()

	# open the socket
	print 'Connecting...' ,
	socket = create_socket(HOST, PORT)
	print 'Connected!'

	listener = ScratchListener(socket)
	sender = ScratchSender(socket)
	listener.start()
	sender.start()
