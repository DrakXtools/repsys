#!/usr/bin/python
#
# This program will convert the output of "svn log" to be suitable
# for usage in an rpm %changelog session.
#
from RepSys import Error
from RepSys.command import *
from RepSys.log import svn2rpm
import getopt
import sys

HELP = """\
Usage: repsys rpmlog [OPTIONS] REPPKGDIRURL

Options:
    -r REV   Collect logs from given revision to revision 0
    -n NUM   Output only last NUM entries
    -T FILE  %changelog template file to be used
    -h       Show this message

Examples:
    repsys rpmlog https://repos/snapshot/python
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.add_option("-r", dest="revision")
    parser.add_option("-n", dest="size", type="int")
    parser.add_option("-T", "--template", dest="template", type="string")
    opts, args = parser.parse_args()
    if len(args) != 1:
        raise Error, "invalid arguments"
    opts.pkgdirurl = default_parent(args[0])
    return opts

def rpmlog(pkgdirurl, revision, size, template):
    sys.stdout.write(svn2rpm(pkgdirurl, revision, size, template=template))

def main():
    do_command(parse_options, rpmlog)

# vim:sw=4:ts=4:et
