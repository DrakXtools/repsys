from MgaRepo import Error, disable_mirror
from MgaRepo.command import *
from MgaRepo.layout import package_url
from MgaRepo.rpmutil import get_spec
import getopt
import sys

HELP = """\
Usage: mgarepo getspec [OPTIONS] REPPKGURL

Prints the .spec file of a given package.

Options:
    -t DIR  Use DIR as target for spec file (default is ".")
    -M      Do not use the mirror (use the main repository)
    -h      Show this message

Examples:
    mgarepo getspec pkgname
    mgarepo getspec svn+ssh://svn.mageia.org/svn/packages/cauldron/pkgname
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.add_option("-t", dest="targetdir", default=".")
    parser.add_option("-M", "--no-mirror", action="callback",
            callback=disable_mirror)
    opts, args = parser.parse_args()
    if len(args) != 1:
        raise Error("invalid arguments")
    opts.pkgdirurl = package_url(args[0])
    return opts

def main():
    do_command(parse_options, get_spec)

# vim:et:ts=4:sw=4
