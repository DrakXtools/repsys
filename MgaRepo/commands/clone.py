#!/usr/bin/python
from MgaRepo import Error
from MgaRepo.command import *
from MgaRepo.rpmutil import clone
import getopt
import sys

HELP = """\
Usage: mgarepo co [OPTIONS] URL [LOCALPATH]

Clone the package source from the Mageia repository.

If the 'mirror' option is enabled, the package is obtained from the mirror
repository.

You can specify the distro branch to checkout from by using distro/pkgname.

Options:
    -d      The distribution branch to checkout from
    -b      The package branch
    -M      Do not use the mirror (use the main repository)
    -h      Show this message
    -F      Do not convert svn usernames to full name & email

Examples:
    mgarepo co pkgname
    mgarepo co -d 1 pkgname
    mgarepo co 1/pkgame
    mgarepo co http://repos/svn/cnc/snapshot/foo
    mgarepo co http://repos/svn/cnc/snapshot/foo foo-pkg
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.add_option("--distribution", "-d", dest="distro", default=None)
    parser.add_option("--branch", "-b", dest="branch", default=None)
    parser.add_option("-F", dest="fullnames", default=True,
            action="store_false")
    opts, args = parser.parse_args()
    if len(args) not in (1, 2):
        raise Error("invalid arguments")
    # here we don't use package_url in order to notify the user we are
    # using the mirror
    opts.pkgdirurl = args[0]
    if len(args) == 2:
        opts.path = args[1]
    else:
        opts.path = None
    return opts

def main():
    do_command(parse_options, clone)

# vim:et:ts=4:sw=4
