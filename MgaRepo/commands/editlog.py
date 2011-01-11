#!/usr/bin/python
from MgaRepo import Error
from MgaRepo.command import *
from MgaRepo.layout import package_url
from MgaRepo.svn import SVN
import re

HELP = """\
Usage: mgarepo editlog [OPTIONS] [URL] REVISION

Options:
    -h         Show this message

Examples:
    mgarepo editlog 14800
    mgarepo editlog https://repos/svn/cnc/snapshot 14800
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
