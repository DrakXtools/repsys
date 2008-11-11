#!/usr/bin/python
from RepSys import Error
from RepSys.command import *
from RepSys.layout import package_url
from RepSys.svn import SVN
import re

HELP = """\
Usage: repsys editlog [OPTIONS] [URL] REVISION

Options:
    -h         Show this message

Examples:
    repsys editlog 14800
    repsys editlog https://repos/svn/cnc/snapshot 14800
"""

def parse_options():
    parser = OptionParser(help=HELP)
    opts, args = parser.parse_args()
    if len(args) == 2:
        pkgdirurl, revision = args
    elif len(args) == 1:
        pkgdirurl, revision = "", args[0]
    else:
        raise Error, "invalid arguments"
    opts.pkgdirurl = package_url(pkgdirurl, mirrored=False)
    opts.revision = re.compile(r".*?(\d+).*").sub(r"\1", revision)
    return opts

def editlog(pkgdirurl, revision):
    svn = SVN()
    svn.propedit("svn:log", pkgdirurl, rev=revision)

def main():
    do_command(parse_options, editlog)

# vim:et:ts=4:sw=4
