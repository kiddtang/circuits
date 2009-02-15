# Module:	__init__
# Date:		1st February 2009
# Author:	James Mills, prologic at shortcircuit dot net dot au

"""Circuits Library - Drivers

circuits.lib.drivers contains drivers for other sources of events.
"""

class DriverError(Exception): pass

from pygame_driver import PyGameDriver