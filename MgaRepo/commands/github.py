#!/usr/bin/python
from MgaRepo import Error
from MgaRepo.command import *
from MgaRepo.GitHub import GitHub
import getopt
import sys

HELP = """\
Usage: mgarepo github [OPTIONS] URL

Import a git-svn cloned repository to github

Options:
    -h      Show this message

Examples:
    mgarepo github import existingpkg
    mgarepo github import svn://svn.mageia.org/svn/packages/cauldron/existingpkg
"""

def github_import(target=".", **kwargs):
    github = GitHub()
    github.import_package(target)

def github_delete(pkg, **kwargs):
    github = GitHub()
    github.delete_repository(pkg)

def parse_options():
    parser = OptionParser(help=HELP)
    opts, args = parser.parse_args()
    if len(args) < 2:#not in (2, 3):
        raise Error("invalid arguments")
    opts.func = globals().get("github_"+args[0], None)
    if args[0] == "import":
        opts.target = args[1]
    elif args[0] == "delete":
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
