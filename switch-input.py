#!/usr/bin/env python

# Script to switch inputs on a TV backlighting system.
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
import os
import json
import sys

if len(sys.argv) < 2:
	print "Usage: %s <input number>" % sys.argv[0]
	sys.exit()

# Load the configuration.
if not os.path.exists('config.json'):
	print "No config.json found - please create and try again."
	sys.exit()

configuration = json.loads(open('config.json').read())

def change_input(inp, colour):
	message = ''
	message += 'I'
	message += struct.pack('<B', inp)
	message += struct.pack('<I', colour)
	return message

def send_message(host, port, message):
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.sendto(message, (host, port))

if __name__ == '__main__':
	send_message(configuration['host'], configuration['port'], change_input(int(sys.argv[1]), 0x000000))
