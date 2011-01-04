#!/usr/bin/python
from RepSys import Error
from RepSys.command import *
from RepSys.layout import package_url
from RepSys.rpmutil import put_srpm
import getopt
import sys, os

HELP = """\
Usage: repsys putsrpm [OPTIONS] SOURCERPMS

Will import source RPMs into the SVN repository.

If the package was already imported, it will add the new files and remove
those not present in the source RPM.

Options:
    -m LOG  Log message used when commiting changes
    -t      Create version-release tag on releases/
    -b NAME The distribution branch to place it
    -d URL  The URL of base directory where packages will be placed
    -c URL  The URL of the base directory where the changelog will be
            placed
    -s      Don't strip the changelog from the spec
            (nor import it into misc/)
    -n      Don't try to rename the spec file
    -h      Show this message

Examples:
    repsys putsrpm pkg/SRPMS/pkg-2.0-1.src.rpm
    repsys putsrpm -b 2009.1 foo-1.1-1.src.rpm
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.add_option("-l", dest="logmsg", default="")
    parser.add_option("-t", dest="markrelease", action="store_true",
            default=False)
    parser.add_option("-s", dest="striplog", action="store_false",
            default=True)
    parser.add_option("-b", dest="branch", type="string", default=None)
    parser.add_option("-d", dest="baseurl", type="string", default=None)
    parser.add_option("-c", dest="baseold", type="string", default=None)
    parser.add_option("-n", dest="rename", action="store_false",
            default=True)
    opts, args = parser.parse_args()
    opts.srpmfiles = args
    return opts

def put_srpm_cmd(srpmfiles, markrelease=False, striplog=True, branch=None,
        baseurl=None, baseold=None, logmsg=None, rename=False):
    for path in srpmfiles:
        put_srpm(path, markrelease, striplog, branch, baseurl, baseold,
                logmsg, rename)

def main():
    do_command(parse_options, put_srpm_cmd)

# vim:et:ts=4:sw=4
