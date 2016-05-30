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
    -P USER    Define the RPM packager information to USER
    -q         Silent build output

"""

def parse_options():
    parser = OptionParser(HELP)
    parser.add_option("-b", dest="build_cmd", default="a")
    parser.add_option("-P", dest="packager", default="")
    parser.add_option("-q", "--quiet", dest="verbose", action="store_false", default=True)
    parser.add_option("-l", dest="rpmlint", action="store_false", default=True)
    opts, args = parser.parse_args()
    return opts

def main():
    do_command(parse_options, build_rpm)

# vim:et:ts=4:sw=4
