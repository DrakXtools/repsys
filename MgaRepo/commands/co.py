#!/usr/bin/python
from MgaRepo import Error, disable_mirror
from MgaRepo.command import *
from MgaRepo.rpmutil import checkout
import getopt
import sys

HELP = """\
Usage: mgarepo co [OPTIONS] URL [LOCALPATH]

Checkout the package source from the Mageia repository.

If the 'mirror' option is enabled, the package is obtained from the mirror
repository.

You can specify the distro branch to checkout from by using distro/pkgname.

Options:
    -d      The distribution branch to checkout from
    -b      The package branch
    -r REV  Revision to checkout
    -s      Only checkout the SPECS/ directory
    -M      Do not use the mirror (use the main repository)
    -h      Show this message

Examples:
    mgarepo co pkgname
    mgarepo co -d 1 pkgname
    mgarepo co 1/pkgame
    mgarepo co http://repos/svn/cnc/snapshot/foo
    mgarepo co http://repos/svn/cnc/snapshot/foo foo-pkg
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.add_option("-r", dest="revision")
    parser.add_option("--distribution", "-d", dest="distro", default=None)
    parser.add_option("--branch", "-b", dest="branch", default=None)
    parser.add_option("-s", "--spec", dest="spec", default=False,
            action="store_true")
    parser.add_option("-M", "--no-mirror", action="callback",
            callback=disable_mirror)
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
    do_command(parse_options, checkout)

# vim:et:ts=4:sw=4
