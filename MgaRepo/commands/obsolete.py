#
# This program will try to patch a spec file from a given package url.
#
from MgaRepo import Error
from MgaRepo.rpmutil import obsolete
from MgaRepo.command import *
import getopt
import sys

HELP = """\
Usage: mgarepo obsolete [Options] PKG

It will move the package to obsolete.

Options:
    -m LOG  Use LOG as log message
    -h      Show this message

Examples:
    mgarepo obsolete foo
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.add_option("-m", dest="log", default=None)
    opts, args = parser.parse_args()
    if len(args) != 1:
        raise Error("invalid arguments")
    opts.pkgdirurl = args[0]
    return opts

def main():
    do_command(parse_options, obsolete)

# vim:et:ts=4:sw=4
