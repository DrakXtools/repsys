from RepSys import Error
from RepSys.command import *
from RepSys.layout import package_url
from RepSys.rpmutil import create_package
import getopt
import sys

HELP = """\
Usage: repsys create [OPTIONS] URL

Creates the minimal structure of a package in the repository.

Options:
    -h      Show this message

Examples:
    repsys create newpkg
    repsys create svn+ssh://svn.mageia.org/svn/packages/cauldron/newpkg
"""

def parse_options():
    parser = OptionParser(help=HELP)
    opts, args = parser.parse_args()
    if len(args) != 1:
        raise Error("invalid arguments")
    opts.pkgdirurl = package_url(args[0], mirrored=False)
    opts.verbose = 1 # Unconfigurable
    return opts

def main():
    do_command(parse_options, create_package)

# vim:et:ts=4:sw=4
