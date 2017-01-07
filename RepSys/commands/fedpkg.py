from RepSys import Error
from RepSys.command import *
from RepSys.GitFedora import GitFedora
import getopt
import sys

HELP = """\
Usage: repsys fedpkg [OPTIONS]

Clones and downloads binary files from fedora package repositories.

Options:
    -h      Show this message

Examples:
    repsys fedpkg clone <pkgname>
"""
def fedpkg_clone(pkg, **kwargs):
    fedpkg = GitFedora(pkg)
    fedpkg.clone_repository(pkg)

def parse_options():
    parser = OptionParser(help=HELP)
    opts, args = parser.parse_args()
    if len(args) < 1:
        raise Error("invalid arguments")
    opts.func = globals().get("fedpkg_"+args[0], None)
    if args[0] == "clone":
        opts.pkg = args[1]
    else:
        raise Error("invalid arguments: %s" % str(args))
    return opts

def dispatch_cmd(*args, **kwargs):
    func = kwargs.pop("func", None)
    if func:
        func(**kwargs)
    else:
        raise Error("invalid command: %s %s" % (sys.argv[0], sys.argv[1]))

def main():
    do_command(parse_options, dispatch_cmd)

# vim:et:ts=4:sw=4
