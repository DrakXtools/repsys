#!/usr/bin/python
from RepSys import Error
from RepSys.command import *
from RepSys.layout import package_url
from RepSys.rpmutil import check_changed
import getopt
import sys

HELP = """\
Usage: repsys changed [OPTIONS] URL

Shows if there are pending changes since the last package release.

Options:
    -a      Check all packages in given URL
    -s      Show differences
    -M      Do not use the mirror (use the main repository)
    -h      Show this message

Examples:
    repsys changed http://repos/svn/cnc/snapshot/foo
    repsys changed -a http://repos/svn/cnc/snapshot
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.add_option("-a", dest="all", action="store_true")
    parser.add_option("-s", dest="show", action="store_true")
    opts, args = parser.parse_args()
    if len(args) != 1:
        raise Error, "invalid arguments"
    opts.pkgdirurl = package_url(args[0])
    opts.verbose = 1 # Unconfigurable
    return opts

def main():
    do_command(parse_options, check_changed)

# vim:et:ts=4:sw=4
