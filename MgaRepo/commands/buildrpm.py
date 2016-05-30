#!/usr/bin/python
#
from MgaRepo.command import do_command
from MgaRepo.rpmutil import build_rpm
from optparse import *

HELP = """\
Usage: mgarepo buildrpm [OPTIONS]

Builds the binary RPM(s) (.rpm) file(s) of a given package.

Options:
    -l         Disable rpmlint check of packages built
"""

def parse_options():
    parser = OptionParser(HELP)
    parser.add_option("-b", dest="build_cmd", default="a")
    parser.add_option("-P", dest="packager", default="")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true", default=False)
    parser.add_option("-l", dest="rpmlint", action="store_false", default=True)
    opts, args = parser.parse_args()
    return opts

def main():
    do_command(parse_options, build_rpm)

# vim:et:ts=4:sw=4
