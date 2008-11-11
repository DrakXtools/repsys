#!/usr/bin/python
import re
import os
import tempfile

import ConfigParser

config = ConfigParser.Config()
tempfile.tempdir = config.get("global", "tempdir", None) or None # when ""
del ConfigParser

class Error(Exception): pass

# vim:et:ts=4:sw=4
