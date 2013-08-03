#!/usr/bin/env python

# Script send test commands to the TV backlighting system.
#
# Copyright 2013 Daniel Foote.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket
import struct

UDP_IP = "10.0.14.200"
UDP_PORT = 8888

def change_input(inp, colour):
	message = ''
	message += 'I'
	message += struct.pack('<B', inp)
	message += struct.pack('<I', colour)
	return message

def send_pixel_header(inp, total):
	message = ''
	message += 'P'
	message += struct.pack('<B', inp)
	message += struct.pack('<H', total)
	return message

def send_pixel(colour):
	return struct.pack('<I', colour)

def send_message(host, port, message):
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.sendto(message, (UDP_IP, UDP_PORT))

if __name__ == '__main__':

	total = 150
	send_message(UDP_IP, UDP_PORT, change_input(1, 0x000000))

	message = send_pixel_header(1, total)
	for i in range(total / 3):
		message += send_pixel(0xFF0000)
		message += send_pixel(0x00FF00)
		message += send_pixel(0x0000FF)

	send_message(UDP_IP, UDP_PORT, message)
