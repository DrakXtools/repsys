#!/usr/bin/python
#
# This program will append a release to the Conectiva Linux package
# repository system.  It's meant to be a startup system to include
# pre-packaged SRPMS in the repository, thus, you should not commit
# packages over an ongoing package structure (with changes in current/
# directory and etc). Also, notice that packages must be included in
# cronological order.
#
from RepSys import Error
from RepSys.command import *
from RepSys.layout import package_url
from RepSys.rpmutil import put_srpm
import getopt
import sys, os

HELP = """\
*** WARNING --- You probably SHOULD NOT use this program! --- WARNING ***

Usage: repsys putsrpm [OPTIONS] REPPKGURL

Options:
    -n      Append package name to provided URL
    -l LOG  Use log when commiting changes
    -h      Show this message

Examples:
    repsys putsrpm file://svn/cnc/snapshot/foo /cnc/d/SRPMS/foo-1.0.src.rpm
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.add_option("-l", dest="log", default="")
    parser.add_option("-n", dest="appendname", action="store_true")
    opts, args = parser.parse_args()
    if len(args) != 2:
        raise Error, "invalid arguments"
    opts.pkgdirurl = package_url(args[0], mirrored=False)
    opts.srpmfile = args[1]
    return opts

def put_srpm_cmd(pkgdirurl, srpmfile, appendname=0, log=""):
    if os.path.isdir(srpmfile):
        dir = srpmfile
        for entry in os.listdir(dir):
            if entry[-8:] == ".src.rpm":
                sys.stderr.write("Putting %s... " % entry)
                sys.stderr.flush()
                entrypath = os.path.join(dir, entry)
                try:
                    put_srpm(pkgdirurl, entrypath, appendname, log)
                    sys.stderr.write("done\n")
                except Error, e:
                    sys.stderr.write("error: %s\n" % str(e))
    else:
        put_srpm(pkgdirurl, srpmfile, appendname, log)
        
                 
def main():
    do_command(parse_options, put_srpm_cmd)

# vim:et:ts=4:sw=4
