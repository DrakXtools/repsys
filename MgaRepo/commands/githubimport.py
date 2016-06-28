#!/usr/bin/python
from MgaRepo import Error
from MgaRepo.command import *
from MgaRepo.GitHub import GitHub
import getopt
import sys

HELP = """\
Usage: mgarepo github-import [OPTIONS] URL

Import a git-svn cloned repository to github

Options:
    -h      Show this message

Examples:
    mgarepo githubimport existingpkg
    mgarepo githubimport svn+ssh://svn.mageia.org/svn/packages/cauldron/existingpkg
"""

def githubimport(target="."):
    github = GitHub()
    github.import_package(target)

def parse_options():
    parser = OptionParser(help=HELP)
    opts, args = parser.parse_args()
    return opts

def main():
    do_command(parse_options, githubimport)

# vim:et:ts=4:sw=4
