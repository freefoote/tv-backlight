#!/usr/bin/env python

# OSX script to capture the screen and format the pixels for sending
# to a TV Backlighting system.
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

# NOTE: Some parts of this script are based off code found on StackOverflow.
# The appropriate StackOverflow conversation is linked in that case.
# Thankyou for posting your questions and code; by sharing we all learn more!

import time
import struct
import sys
import socket
import json
import os

import LaunchServices
import Quartz.CoreGraphics as CG
from Cocoa import NSURL
import Quartz

# Configuration defaults.
configuration = {
    # Target host and port number.
    'host': "10.0.14.200",
    'port': 8888,

    # The number of pixels actually attached to the TV.
    'size_x': 46,
    'size_y': 26,

    # The number of frames to average together (to stop flashing/flickering)
    'average_frames': 32,

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
    'colour_divisor': 2
}

# Load the configuration.
if not os.path.exists('config.json'):
    print "No config.json found - please create and try again."
    sys.exit()

configuration.update(json.loads(open('config.json').read()))

# http://stackoverflow.com/questions/12978846/python-get-screen-pixel-value-in-os-x/13024603#13024603
class ScreenPixel(object):
    """Captures the screen using CoreGraphics, and provides access to
    the pixel values.
    """

    def __init__(self, config):
        self.target_width = config['size_x']
        self.target_height = config['size_y']
        self.colour_scale = config['colour_divisor']
        self.average_frames = config['average_frames']

        self.last_values = {}

    def capture(self, region = None):
        """region should be a CGRect, something like:

        >>> import Quartz.CoreGraphics as CG
        >>> region = CG.CGRectMake(0, 0, 100, 100)
        >>> sp = ScreenPixel()
        >>> sp.capture(region=region)

        The default region is CG.CGRectInfinite (captures the full screen)
        """

        if region is None:
            region = CG.CGRectInfinite
        else:
            # TODO: Odd widths cause the image to warp. This is likely
            # caused by offset calculation in ScreenPixel.pixel, and
            # could could modified to allow odd-widths
            if region.size.width % 2 > 0:
                emsg = "Capture region width should be even (was %s)" % (
                    region.size.width)
                raise ValueError(emsg)

        # Create screenshot as CGImage
        image = CG.CGWindowListCreateImage(
            region,
            CG.kCGWindowListOptionAll,
            CG.kCGNullWindowID,
            CG.kCGWindowImageDefault)

        self.captime = time.time()

        # Get width/height of image
        self.screen_width = CG.CGImageGetWidth(image)
        self.screen_height = CG.CGImageGetHeight(image)

        # http://www.gotow.net/creative/wordpress/?p=7
        colourspace = CG.CGImageGetColorSpace(image)
        context = CG.CGBitmapContextCreate(
            None,
            self.target_width,
            self.target_height,
            8, # CG.CGImageGetBitsPerComponent(image),
            self.target_width * 4, # CG.CGImageGetBytesPerRow(image),
            colourspace,
            CG.CGImageGetAlphaInfo(image)
        )

        CG.CGContextSetInterpolationQuality(context, CG.kCGInterpolationNone)

        CG.CGContextDrawImage(context, CG.CGRectMake(0, 0, self.target_width, self.target_height), image)

        result = CG.CGBitmapContextCreateImage(context)

        # Code to save the result to file, for testing and debugging.
        # url = NSURL.fileURLWithPath_('screenshot.png')
        # dest = Quartz.CGImageDestinationCreateWithURL(
        #     url,
        #     LaunchServices.kUTTypePNG,
        #     1,
        #     None
        # )
        # properties = {
        #     Quartz.kCGImagePropertyDPIWidth: 72,
        #     Quartz.kCGImagePropertyDPIHeight: 72
        # }
        # Quartz.CGImageDestinationAddImage(dest, result, properties)
        # Quartz.CGImageDestinationFinalize(dest)

        # Intermediate step, get pixel data as CGDataProvider
        prov = CG.CGImageGetDataProvider(result)

        # Copy data out of CGDataProvider, becomes string of bytes
        self._data = CG.CGDataProviderCopyData(prov)

        del prov
        del result
        del image
        del context
        del colourspace

    def pixel(self, x, y):
        """Get pixel value at given (x,y) screen coordinates

        Must call capture first.
        """

        # Pixel data is unsigned char (8bit unsigned integer),
        # and there are for (blue,green,red,alpha)
        data_format = "BBBB"

        # Calculate offset, based on
        # http://www.markj.net/iphone-uiimage-pixel-color/
        offset = 4 * ((self.target_width*int(round(y))) + int(round(x)))

        # Unpack data from string into Python'y integers
        # Original internet code had this:
        # b, g, r, a = struct.unpack_from(data_format, self._data, offset=offset)
        # But it turns out this is the correct order:
        a, r, g, b = struct.unpack_from(data_format, self._data, offset=offset)

        r = r / self.colour_scale
        g = g / self.colour_scale
        b = b / self.colour_scale

        result_key_r = "%d_%d_r" % (x, y)
        result_key_g = "%d_%d_g" % (x, y)
        result_key_b = "%d_%d_b" % (x, y)

        if result_key_r not in self.last_values:
            self.last_values[result_key_r] = []
        if result_key_g not in self.last_values:
            self.last_values[result_key_g] = []
        if result_key_b not in self.last_values:
            self.last_values[result_key_b] = []

        if len(self.last_values[result_key_r]) >= self.average_frames:
            self.last_values[result_key_r] = self.last_values[result_key_r][1:]
        if len(self.last_values[result_key_g]) >= self.average_frames:
            self.last_values[result_key_g] = self.last_values[result_key_g][1:]
        if len(self.last_values[result_key_b]) >= self.average_frames:
            self.last_values[result_key_b] = self.last_values[result_key_b][1:]

        self.last_values[result_key_r].append(r)
        self.last_values[result_key_g].append(g)
        self.last_values[result_key_b].append(b)

        r = sum(self.last_values[result_key_r]) / len(self.last_values[result_key_r])
        g = sum(self.last_values[result_key_g]) / len(self.last_values[result_key_g])
        b = sum(self.last_values[result_key_b]) / len(self.last_values[result_key_b])

        colour = (r * 256 * 256) + (g * 256) + b
        return colour

# Cap the first time to get the window size.
capture = ScreenPixel(configuration)
capture.capture()
width = capture.screen_width
height = capture.screen_height
print "The size of the window is %d x %d" % (width, height)

# Calculations for later on.
arduino_pixels = ((configuration['size_x'] * 2) + (configuration['size_y'] * 2)) - 4
black_bar_probe_points = [0, configuration['size_x'] / 4, configuration['size_x'] / 2, int(configuration['size_x'] * 0.75), configuration['size_x'] - 1]
black_bar_top_candidates = [0] * configuration['black_bar_candidate_length']
black_bar_bottom_candidates = [0] * configuration['black_bar_candidate_length']
black_bar_top_candidate_index = 0
black_bar_bottom_candidate_index = 0

print "Sending %d pixels each screen." % arduino_pixels

while True:
    start = time.time()

    # Fetch, scale down.
    capture.capture()

    captime = capture.captime

    scaletime = time.time()

    real_height = capture.target_height - 1
    real_width = capture.target_width - 1

    # Search for the black bars.
    black_top = 0
    black_bottom = real_height

    top_candidates = []
    bottom_candidates = []

    for x in black_bar_probe_points:
        this_top = 0
        this_bottom = real_height
        for y in range(configuration['black_bar_search_height']):
            colour = capture.pixel(x, y)
            if colour == 0x0:
                this_top = y + 1
            colour = capture.pixel(x, real_height - y)
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
        colour = capture.pixel(x, y)
        # print "%d, %d: %X" % (x, y, colour)
        network_message += struct.pack('<I', colour)

    # Right side, bottom to top.
    x = real_width
    for y in range(real_height, 0, -1):
        colour = capture.pixel(x, y)
        # print "%d, %d: %X" % (x, y, colour)
        network_message += struct.pack('<I', colour)

    # Top side, right to left.
    y = black_top
    for x in range(real_width, 0, -1):
        colour = capture.pixel(x, y)
        # print "%d, %d: %X" % (x, y, colour)
        network_message += struct.pack('<I', colour)

    # Left side, top to bottom.
    x = 0
    for y in range(real_height):
        colour = capture.pixel(x, y)
        # print "%d, %d: %X" % (x, y, colour)
        network_message += struct.pack('<I', colour)

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(network_message, (configuration['host'], configuration['port']))
    except socket.error, ex:
        # Unable to send. On OSX, this happens as it resumes from
        # sleep whilst the network comes back.
        # Wait for a bit and then try again.
        print str(ex)
        print "Retrying shortly."
        time.sleep(2)

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
