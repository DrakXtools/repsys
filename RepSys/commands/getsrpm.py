#!/usr/bin/python
#
# This program will extract given version/revision of the named package
# from the Conectiva Linux repository system.
#
from RepSys import Error, config
from RepSys.command import *
from RepSys.rpmutil import get_srpm
import tempfile
import shutil
import getopt
import glob
import sys
import os

HELP = """\
Usage: repsys getsrpm [OPTIONS] REPPKGURL

Generates the source RPM (.srpm) file of a given package.

Options:
    -c         Use files in current/ directory (default)
    -p         Use files in pristine/ directory
    -v VER     Use files from the version specified by VER (e.g. 2.2.1-2cl)
    -r REV     Use files from current directory, in revision REV (e.g. 1001)
    -t DIR     Put SRPM file in directory DIR when done (default is ".")
    -P USER    Define the RPM packager inforamtion to USER
    -s FILE    Run script with "FILE TOPDIR SPECFILE" command
    -n         Rename the package to include the revision number
    -l         Use subversion log to build rpm %changelog
    -T FILE    Template to be used to generate the %changelog
    -h         Show this message
    --strict   Check if the given revision contains changes in REPPKGURL

Examples:
    repsys getsrpm python
    repsys getsrpm -l python
    repsys getsrpm http://foo.bar/svn/cnc/snapshot/python
    repsys getsrpm -p http://foo.bar/svn/cnc/releases/8cl/python
    repsys getsrpm -r 1001 file:///svn/cnc/snapshot/python
"""

def mode_callback(option, opt, val, parser, mode):
    opts = parser.values
    opts.mode = mode
    if mode == "version":
        try:
            opts.version, opts.release = val.split("-", 1)
        except ValueError:
            raise Error, "wrong version, use something like 2.2-1mdk"
    elif mode == "revision":
        opts.revision = val

def parse_options():
    parser = OptionParser(help=HELP)
    parser.defaults["mode"] = "current"
    parser.defaults["version"] = None
    parser.defaults["release"] = None
    parser.defaults["revision"] = None
    parser.defaults["submit"] = False
    callback_options = dict(action="callback", callback=mode_callback,
                            type="string", dest="__ignore")
    parser.add_option("-c", callback_kwargs={"mode": "current"}, nargs=0,
                      **callback_options)
    parser.add_option("-p", callback_kwargs={"mode": "pristine"}, nargs=0,
                      **callback_options)
    parser.add_option("-r", callback_kwargs={"mode": "revision"}, nargs=1,
                      **callback_options)
    parser.add_option("-v", callback_kwargs={"mode": "version"}, nargs=1,
                      **callback_options)
    parser.add_option("-t", dest="targetdirs", action="append", default=[])
    parser.add_option("-s", dest="scripts", action="append", default=[])
    parser.add_option("-P", dest="packager", default="")
    parser.add_option("-n", dest="revname", action="store_true")
    parser.add_option("-l", dest="svnlog", action="store_true")
    parser.add_option("-T", dest="template", type="string", default=None)
    parser.add_option("--strict", dest="strict", default=False,
            action="store_true")
    opts, args = parser.parse_args()
    del opts.__ignore
    if len(args) != 1:
        raise Error, "invalid arguments"
    opts.pkgdirurl = default_parent(args[0])
    opts.verbose = 1
    return opts

def main():
    do_command(parse_options, get_srpm)

# vim:et:ts=4:sw=4
