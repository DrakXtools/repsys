import re
import os
import tempfile

from . import ConfigParser

config = ConfigParser.Config()
tempfile.tempdir = config.get("global", "tempdir", None) or None # when ""
del ConfigParser

def disable_mirror(*a, **kw):
    config.set("global", "use-mirror", "no")

class Error(Exception): pass

class SilentError(Error): pass

# vim:et:ts=4:sw=4
