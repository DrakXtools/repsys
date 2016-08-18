#
# This program will append a release to the Conectiva Linux package
# repository system.  It's meant to be a startup system to include
# pre-packaged SRPMS in the repository, thus, you should not commit
# packages over an ongoing package structure (with changes in current/
# directory and etc). Also, notice that packages must be included in
# cronological order.
#
from MgaRepo import Error
from MgaRepo.command import *
from MgaRepo.layout import package_url
from MgaRepo.simplerpm import SRPM
from MgaRepo.rpmutil import mark_release
from MgaRepo.util import get_auth
import getopt
import sys
import os

HELP = """\
*** WARNING --- You probably SHOULD NOT use this program! --- WARNING ***

Usage: mgarepo markrelease [OPTIONS] REPPKGURL

This subcommand creates a 'tag' for a given revision of a given package.

The tag will be stored in the directory releases/ inside the package
structure.

Options:
    -f FILE Try to extract information from given file
    -r REV  Revision which will be used to make the release copy tag
    -v VER  Version which will be used to make the release copy tag
    -n      Append package name to provided URL
    -h      Show this message

Examples:
    mgarepo markrelease -r 68 -v 1.0-1 file://svn/cnc/snapshot/foo
    mgarepo markrelease -f @68:foo-1.0-1.src.rpm file://svn/cnc/snapshot/foo
    mgarepo markrelease -r 68 -f foo-1.0.src.rpm file://svn/cnc/snapshot/foo
"""

def version_callback(option, opt, val, parser):
    opts = parser.values
    try:
        opts.version, opts.release = val.split("-", 1)
    except ValueError:
        raise Error("wrong version, use something like 1:2.2-1mdk")

def parse_options():
    parser = OptionParser(help=HELP)
    parser.defaults["version"] = None
    parser.defaults["release"] = None
    parser.add_option("-v", action="callback", callback=version_callback,
            nargs=1, type="string", dest="__ignore")
    parser.add_option("-r", dest="revision")
    parser.add_option("-f", dest="filename")
    parser.add_option("-n", dest="appendname", action="store_true")
    opts, args = parser.parse_args()

    if len(args) != 1:
        raise Error("invalid arguments")

    opts.pkgdirurl = package_url(args[0], mirrored=False)

    filename = opts.filename
    appendname = opts.appendname
    del opts.filename, opts.appendname, opts.__ignore

    if filename:
        if not os.path.isfile(filename):
            raise Error("file not found: "+filename)
        if not opts.revision:
            basename = os.path.basename(filename)
            end = basename.find(":")
            if basename[0] != "@" or end == -1:
                raise Error("couldn't guess revision from filename")
            opts.revision = basename[1:end]
        srpm = None
        if not opts.version:
            srpm = SRPM(filename)
            if srpm.epoch:
                opts.version = "%s:%s" % (srpm.epoch, srpm.version)
            else:
                opts.version = srpm.version
            opts.release = srpm.release
        if appendname:
            if not srpm:
                srpm = SRPM(filename)
            opts.pkgdirurl = "/".join([opts.pkgdirurl, srpm.name])
    elif appendname:
        raise Error("option -n requires option -f")
    elif not opts.revision:
        raise Error("no revision provided")
    elif not opts.version:
        raise Error("no version provided")
    #get_auth()
    return opts

def main():
    do_command(parse_options, mark_release)

# vim:et:ts=4:sw=4
