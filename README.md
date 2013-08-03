TV Backlighting system
======================

There are several components that make up this TV Backlighting system.
You can read the writeup about the hardware and the software on my
website:

http://freefoote.dview.net/electronics/tv-backlight

Notes on how to install the various components follow.

Arduino Sketch
--------------

The Arduino sketch is stored in the directory TVBacklight. You should
be able to open this with the Arduino software and then flash it onto your
Arduino.

To build the sketch, you will need the Adafruit Neopixel library, which
you can get from their GitHub repository:

https://github.com/adafruit/Adafruit_NeoPixel

Currently the IP address and UDP port is hard coded into the sketch. You
will want to update these for your local network.

If you have more than 150 pixels attached, you'll also need to update the
max packet size in the sketch. Be aware that there isn't a lot of memory
left on the Arduino at this stage.

Python script - general
-----------------------

Included in the repository is a config.json.sample file. Copy this to
config.json and adjust the variables contained in that file for your
setup.

NOTE: The script supplied has wildly varying performance on different
platforms and configurations, and in many cases might be too slow for
what you want to do.

Python script - Linux
---------------------

To run the Python script on Linux, you only need to install PyGTK and Numpy.
With Ubuntu, you can install this with:

	$ sudo apt-get install python-gtk2 python-numpy

After that, you can execute the script "capture-and-send.py" directly.

Python script - Windows
-----------------------

To run the Python script on Windows, you'll need to download Python 2.7,
PyGTK for Windows, and Scipy (to get the numpy extensions required).

Grab the latest 2.7 package from here:

http://python.org/download/

Grab the latest PyGTK all in one installer from here:

http://www.pygtk.org/downloads.html

Grab the appropriate Scipy package from here:

http://sourceforge.net/projects/scipy/files/scipy/0.12.0/

Install all of these, and then you can launch the python script.
Use capture-and-send.py.

NOTE: You will need to disable Aero on Windows 7 to get an acceptable
capture performance.

Python script - OSX
-------------------

On a recent OSX (tested on 10.8) you should already have everything you
need installed. You can just run the capture-and-send-osx.py script
directly to get it working.

The OSX script uses CoreGraphics to capture the screen and calculate the
edge pixels, which was more appropriate for that platform.

Out of the box on my 2012 Mac Mini, it captures upwards of 40 frames per
second.

NOTE: In certain applications, specifically iTunes, you'll only get a
white image back. This is due to the copy protection built into iTunes.