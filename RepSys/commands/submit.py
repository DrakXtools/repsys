#!/usr/bin/python
from RepSys import Error, config
from RepSys.command import *
from RepSys.rpmutil import get_spec, get_submit_info
from RepSys.util import get_auth, execcmd
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

Options:
    -t TARGET  Submit given package URL to given target
    -l         Just list available targets
    -h         Show this message

Examples:
    repsys submit
    repsys submit foo 14800
    repsys submit https://repos/svn/cnc/snapshot/foo 14800
    repsys submit -l https://repos
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.defaults["revision"] = ""
    parser.add_option("-t", dest="target", default="Cooker")
    parser.add_option("-l", dest="list", action="store_true")
    opts, args = parser.parse_args()
    if not args:
        name, rev = get_submit_info(".")
        try:
            yn = raw_input("Submit '%s', revision %d (y/N)? " % (name, rev))
        except KeyboardInterrupt:
            yn = "n"
        if yn.lower() in ("y", "yes"):
            args = name, str(rev)
        else:
            print "Cancelled."
            sys.exit(1)
    elif len(args) > 2:
        raise Error, "invalid arguments"
    opts.pkgdirurl = default_parent(args[0])
    if len(args) == 2:
        opts.revision = re.compile(r".*?(\d+).*").sub(r"\1", args[1])
    elif not opts.list:
        raise Error, "provide -l or a revision number"
    return opts

def submit(pkgdirurl, revision, target, list=0):
    #if not NINZ:
    #    raise Error, "you must have NINZ installed to use this command"
    type, rest = urllib.splittype(pkgdirurl)
    host, path = urllib.splithost(rest)
    user, host = urllib.splituser(host)
    host, port = urllib.splitport(host)
    if type != "https" and type != "svn+ssh":
        raise Error, "you must use https:// or svn+ssh:// urls"
    if user:
        user, passwd = urllib.splitpasswd(user)
        if passwd:
            raise Error, "do not use a password in your command line"
    if type == "https":
        user, passwd = get_auth(username=user)
        #soap = NINZ.client.Binding(host=host,
        #                           url="https://%s/scripts/cnc/soap" % host,
        #                           ssl=1,
        #                           auth=(NINZ.client.AUTH.httpbasic,
        #                                 user, passwd))
        if port:
            port = ":"+port
        else:
            port = ""
        iface = xmlrpclib.ServerProxy("https://%s:%s@%s%s/scripts/cnc/xmlrpc"
                                      % (user, passwd, host, port))
        try:
            if list:
                targets = iface.submit_targets()
                if not targets:
                    raise Error, "no targets available"
                sys.stdout.writelines(['"%s"\n' % x for x in targets])
            else:
                iface.submit_package(pkgdirurl, revision, target)
                print "Package submitted!"
        #except NINZ.client.SoapError, e:
        except xmlrpclib.ProtocolError, e:
            raise Error, "remote error: "+str(e.errmsg)
        except xmlrpclib.Fault, e:
            raise Error, "remote error: "+str(e.faultString)
        except xmlrpclib.Error, e:
            raise Error, "remote error: "+str(e)
    else:
        if list:
            raise Error, "unable to list targets from svn+ssh:// URLs"
        command = "ssh %s /usr/share/repsys/create-srpm '%s' -r %s -t %s" % (
                host, pkgdirurl, revision, target)
        status, output = execcmd(command)
        if status == 0:
            print "Package submitted!"
        else:
            sys.exit(status)


def main():
    do_command(parse_options, submit)

# vim:et:ts=4:sw=4
