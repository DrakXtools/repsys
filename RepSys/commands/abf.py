from RepSys import Error
from RepSys.command import *
from RepSys.GitABF import GitABF
import getopt
import sys

HELP = """\
Usage: repsys abf [OPTIONS]

Clones and downloads binary files from ABF package repositories.

Options:
    -h      Show this message

Examples:
    repsys abf clone <pkgname>
"""
def abf_clone(pkg, **kwargs):
    abf = GitABF(pkg)
    abf.clone_repository()

def parse_options():
    parser = OptionParser(help=HELP)
    opts, args = parser.parse_args()
    if len(args) < 1:
        raise Error("invalid arguments")
    opts.func = globals().get("abf_"+args[0], None)
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
