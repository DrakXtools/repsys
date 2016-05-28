#!/usr/bin/python
from MgaRepo import Error, config
from MgaRepo.command import *
from MgaRepo.util import execcmd, get_helper
import sys


HELP = """\
Usage: 
    Take maintainership of one package :
       mgarepo maintdb set [package] [login]

    Remove yourself from maintainer of a package :
       mgarepo maintdb set [package] nobody

    See who is maintainer of a package :
       mgarepo maintdb get [package]

    See the list of all packages with their maintainer :
       mgarepo maintdb get

"""

def parse_options():
    parser = OptionParser(help=HELP)
    opts, args = parser.parse_args()
    if len(args):
        opts.maintdb_args = args
    else:
        raise Error("you need to provide arguments, see them with --help")
    return opts

def maintdb(maintdb_args):
    host = config.get("maintdb", "host", "maintdb.mageia.org")
    maintdb_helper = get_helper("maintdb")
    command = ["ssh", host, maintdb_helper] + maintdb_args
    execcmd(command, show=True)
    sys.exit(0)

def main():
    do_command(parse_options, maintdb)

# vim:et:ts=4:sw=4
