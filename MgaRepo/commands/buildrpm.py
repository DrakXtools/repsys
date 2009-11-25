#!/usr/bin/python
#
from MgaRepo import Error, config
from MgaRepo.command import *
from MgaRepo.layout import package_url
from MgaRepo.rpmutil import build_rpm
import tempfile
import shutil
from optparse import *
import glob
import sys
import os

HELP = """\
Usage: repsys buildrpm [OPTIONS]

Builds the binary RPM(s) (.rpm) file(s) of a given package.
"""

def parse_options():
    parser = OptionParser(HELP)
    parser.add_option("-b", dest="build_cmd", default="a")
    parser.add_option("-P", dest="packager", default="")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true", default=False)
    opts, args = parser.parse_args()
    return opts

def main():
    do_command(parse_options, build_rpm)

# vim:et:ts=4:sw=4
