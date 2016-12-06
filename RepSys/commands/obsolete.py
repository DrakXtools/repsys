#
# This program will try to patch a spec file from a given package url.
#
from RepSys import Error
from RepSys.rpmutil import obsolete
from RepSys.command import *
import getopt
import sys

HELP = """\
Usage: repsys obsolete [Options] PKG

It will move the package to obsolete.

Options:
    -m LOG  Use LOG as log message
    -h      Show this message

Examples:
    repsys obsolete foo
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
