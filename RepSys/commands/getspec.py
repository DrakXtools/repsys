#!/usr/bin/python
from RepSys import Error
from RepSys.command import *
from RepSys.layout import package_url
from RepSys.rpmutil import get_spec
import getopt
import sys

HELP = """\
Usage: repsys getspec [OPTIONS] REPPKGURL

Prints the .spec file of a given package.

Options:
    -t DIR  Use DIR as target for spec file (default is ".")
    -M      Do not use the mirror (use the main repository)
    -h      Show this message

Examples:
    repsys getspec pkgname
    repsys getspec svn+ssh://svn.mandriva.com/svn/packages/cooker/pkgname
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.add_option("-t", dest="targetdir", default=".")
    opts, args = parser.parse_args()
    if len(args) != 1:
        raise Error, "invalid arguments"
    opts.pkgdirurl = package_url(args[0])
    return opts

def main():
    do_command(parse_options, get_spec)

# vim:et:ts=4:sw=4
