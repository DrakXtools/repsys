#!/usr/bin/python
from RepSys import Error, config
from RepSys.command import *
from RepSys.rpmutil import get_spec, get_submit_info
from RepSys.util import get_auth, execcmd, get_helper
import urllib
import getopt
import sys
import re

#try:
#    import NINZ.client
#except ImportError:
#    NINZ = None

import xmlrpclib

HELP = """\
Usage: repsys submit [OPTIONS] [URL [REVISION]]

Submits the package from URL to the submit host.

The submit host will try to build the package, and upon successful
completion will 'tag' the package and upload it to the official
repositories.

The status of the submit can visualized at:

http://kenobi.mandriva.com/bs/output.php

If no URL and revision are specified, the latest changed revision in 
the package working copy of the current directory will be used.

Options:
    -t TARGET  Submit given package URL to given target
    -l         Just list available targets
    -r REV     Provides a revision number (when not providing as an
               argument)
    -s         The host in which the package URL will be submitted
               (defaults to the host in the URL)
    -h         Show this message
    --define   Defines one variable to be used by the submit scripts 
               in the submit host

Examples:
    repsys submit
    repsys submit foo 14800
    repsys submit https://repos/svn/mdv/cooker/foo 14800
    repsys submit -r 14800 https://repos/svn/mdv/cooker/foo
    repsys submit -l https://repos
    repsys submit --define section=main/testing -t 2008.0
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.defaults["revision"] = ""
    parser.add_option("-t", dest="target", default="Cooker")
    parser.add_option("-l", dest="list", action="store_true")
    parser.add_option("-r", dest="revision", type="string", nargs=1)
    parser.add_option("-s", dest="submithost", type="string", nargs=1,
            default=None)
    parser.add_option("--define", action="append")
    opts, args = parser.parse_args()
    if not args:
        name, rev = get_submit_info(".")
        args = name, str(rev)
        print "submitting %s at revision %s..." % args
    elif len(args) > 2:
        raise Error, "invalid arguments"
    opts.pkgdirurl = default_parent(args[0])
    if len(args) == 2:
        opts.revision = re.compile(r".*?(\d+).*").sub(r"\1", args[1])
    elif len(args) == 1 and opts.revision:
        # accepts -r 3123 http://foo/bar
        pass
    elif not opts.list:
        raise Error, "provide -l or a revision number"
    return opts

def submit(pkgdirurl, revision, target, list=0, define=[], submithost=None):
    #if not NINZ:
    #    raise Error, "you must have NINZ installed to use this command"
    if submithost is None:
        submithost = config.get("submit", "host")
        if submithost is None:
            # extract the submit host from the svn host
            type, rest = urllib.splittype(pkgdirurl)
            host, path = urllib.splithost(rest)
            user, host = urllib.splituser(host)
            submithost, port = urllib.splitport(host)
            del type, user, port, path, rest
    # runs a create-srpm in the server through ssh, which will make a
    # copy of the rpm in the export directory
    if list:
        raise Error, "unable to list targets from svn+ssh:// URLs"
    createsrpm = get_helper("create-srpm")
    command = "ssh %s %s '%s' -r %s -t %s" % (
            submithost, createsrpm, pkgdirurl, revision, target)
    if define:
        command += " " + " ".join([ "--define " + x for x in define ])
    status, output = execcmd(command)
    if status == 0:
        print "Package submitted!"
    else:
        sys.stderr.write(output)
        sys.exit(status)


def main():
    do_command(parse_options, submit)

# vim:et:ts=4:sw=4
