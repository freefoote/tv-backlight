#!/usr/bin/env python

# Script to capture the screen with GTK, and format and send
# to a TV backlighting system.
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

import time
import gtk.gdk
import struct
import sys
import socket
import json
import os

# Configuration defaults.
configuration = {
	# Target host and port number.
	'host': "10.0.14.200",
	'port': 8888,

	# The number of pixels actually attached to the TV.
	'size_x': 46,
	'size_y': 26,

	# The number of frames to average together (to stop flashing/flickering)
	'average_frames': 16,

	# How many pixels to probe looking for black bars.
	'black_bar_search_height': 8,

	# The number of frames to consider the black bar height for.
	# The minimum detected bottom from this length is used.
	# For example, with this at 1024, if we capture at 50fps, then the black bar mininum
	# for the last 20 seconds is used. This makes it a little slow
	# to detect the start of movies, but should allow the detection to work through
	# the movie better, and also deal with non-black-bar videos as well.
	'black_bar_candidate_length': 1024,

	# Divide the colours by this number. This is because the LED
	# strip tends to be super bright, so this crudely dims it down somewhat.
	'colour_divisor': 2,
}

# Load the configuration.
if not os.path.exists('config.json'):
	print "No config.json found - please create and try again."
	sys.exit()

configuration.update(json.loads(open('config.json').read()))

# Get the window size.
window = gtk.gdk.get_default_root_window()
size = window.get_size()
print "The size of the window is %d x %d" % size

# Calculations for later on.
scale_x = float(configuration['size_x']) / float(size[0])
scale_y = float(configuration['size_y']) / float(size[1])
current_buffer = 0
composite_alpha = (255 / configuration['average_frames'])
arduino_pixels = ((configuration['size_x'] * 2) + (configuration['size_y'] * 2)) - 4
black_bar_probe_points = [0, configuration['size_x'] / 4, configuration['size_x'] / 2, int(configuration['size_x'] * 0.75), configuration['size_x'] - 1]
black_bar_top_candidates = [0] * configuration['black_bar_candidate_length']
black_bar_bottom_candidates = [0] * configuration['black_bar_candidate_length']
black_bar_top_candidate_index = 0
black_bar_bottom_candidate_index = 0

print "Sending %d pixels each screen." % arduino_pixels

# Set up the buffers - only once, and we'll reuse them.
screen_contents = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, size[0], size[1])
screen_buffers = []
for i in range(configuration['average_frames']):
	screen_buffers.append(gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, configuration['size_x'], configuration['size_y']))
scaled_contents = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, configuration['size_x'], configuration['size_y'])

def colourfor(pa, x, y, scale = 1):
	"""
	Helper function to get a pixel from a Numpy pixel array and
	reassemble it.
	"""
	raw_pixel = pa[y][x]
	red = raw_pixel[0] / scale
	green = raw_pixel[1] / scale
	blue = raw_pixel[2] / scale
	colour = (red * 256 * 256) + (green * 256) + blue
	return colour

while True:
	start = time.time()

	# Fetch, scale down.
	screen_contents = screen_contents.get_from_drawable(window, window.get_colormap(), 0, 0, 0, 0, size[0], size[1])
	captime = time.time()

	# Scale into the current buffer.
	screen_contents.scale(screen_buffers[current_buffer], 0, 0, configuration['size_x'], configuration['size_y'], 0, 0, scale_x, scale_y, gtk.gdk.INTERP_NEAREST)

	# Wrap the buffer number around, if needed.
	current_buffer += 1
	if current_buffer >= configuration['average_frames']:
		current_buffer = 0

	# Clear the scaled contents, then composite the last frames on top of it.
	scaled_contents.fill(0x00000000)

	for i in range(configuration['average_frames']):
		screen_buffers[i].composite(scaled_contents, 0, 0, configuration['size_x'], configuration['size_y'], 0, 0, 1.0, 1.0, gtk.gdk.INTERP_NEAREST, composite_alpha)

	scaletime = time.time()

	# Debugging code to save the frame that we're just composited.
	#screen_contents.scale(scaled_contents, 0, 0, minisize_x, minisize_y, 0, 0, scale_x, scale_y, gtk.gdk.INTERP_NEAREST)
	#scaled_contents.save("screenshot%d.png" % time.time(), "png")

	real_height = scaled_contents.get_height() - 1
	real_width = scaled_contents.get_width() - 1
	pixel_array = scaled_contents.pixel_array

	# Search for the black bars.
	black_top = 0
	black_bottom = real_height

	top_candidates = []
	bottom_candidates = []

	for x in black_bar_probe_points:
		this_top = 0
		this_bottom = real_height
		for y in range(configuration['black_bar_search_height']):
			colour = colourfor(pixel_array, x, y)
			if colour == 0x0:
				this_top = y + 1
			colour = colourfor(pixel_array, x, real_height - y)
			if colour == 0x0:
				this_bottom = (real_height - y) - 1

		top_candidates.append(this_top)
		bottom_candidates.append(this_bottom)

	black_top = min(*top_candidates)
	black_bottom = max(*bottom_candidates)

	black_bar_top_candidates[black_bar_top_candidate_index] = black_top
	black_bar_bottom_candidates[black_bar_bottom_candidate_index] = black_bottom

	black_bar_top_candidate_index += 1
	if black_bar_top_candidate_index == configuration['black_bar_candidate_length']:
		black_bar_top_candidate_index = 0

	black_bar_bottom_candidate_index += 1
	if black_bar_bottom_candidate_index == configuration['black_bar_candidate_length']:
		black_bar_bottom_candidate_index = 0

	black_top = min(*black_bar_top_candidates)
	black_bottom = max(*black_bar_bottom_candidates)

	# print "Black bars: %d -> %d" % (black_top, black_bottom)

	searchtime = time.time()

	network_message = 'P'
	network_message += struct.pack('<B', configuration['input'])
	network_message += struct.pack('<H', arduino_pixels)

	# Bottom of image first, left to right.
	y = black_bottom
	for x in range(real_width):
		colour = colourfor(pixel_array, x, y, configuration['colour_divisor'])
		# print "%d, %d: %X" % (x, y, colour)
		network_message += struct.pack('<I', colour)

	# Right side, bottom to top.
	x = real_width
	for y in range(real_height, 0, -1):
		colour = colourfor(pixel_array, x, y, configuration['colour_divisor'])
		# print "%d, %d: %X" % (x, y, colour)
		network_message += struct.pack('<I', colour)

	# Top side, right to left.
	y = black_top
	for x in range(real_width, 0, -1):
		colour = colourfor(pixel_array, x, y, configuration['colour_divisor'])
		# print "%d, %d: %X" % (x, y, colour)
		network_message += struct.pack('<I', colour)

	# Left side, top to bottom.
	x = 0
	for y in range(real_height):
		colour = colourfor(pixel_array, x, y, configuration['colour_divisor'])
		# print "%d, %d: %X" % (x, y, colour)
		network_message += struct.pack('<I', colour)

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.sendto(network_message, (configuration['host'], configuration['port']))

	# print "Sent %d bytes." % len(network_message)

	end = time.time()
	print "Total time %0.4fs. Cap %0.4fs, Scale %0.4fs, Search %0.4fs, Proc %0.4fs, FPS %0.2f" % (
		end - start,
		captime - start,
		scaletime - captime,
		searchtime - scaletime,
		end - searchtime,
		1 / (end - start)
	)