from MgaRepo import Error
from MgaRepo.command import *
from MgaRepo.layout import package_url
from MgaRepo.rpmutil import create_package
import getopt
import sys

HELP = """\
Usage: mgarepo create [OPTIONS] URL

Creates the minimal structure of a package in the repository.

Options:
    -h      Show this message

Examples:
    mgarepo create newpkg
    mgarepo create svn+ssh://svn.mageia.org/svn/packages/cauldron/newpkg
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
