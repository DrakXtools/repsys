#!/usr/bin/python
from MgaRepo.command import *
from MgaRepo.rpmutil import switch

HELP = """\
Usage: mgarepo switch [URL]

Relocates the working copy to the base location URL.

If URL is not provided, it will use the option repository from mgarepo.conf
as default, or, if the current working copy is already based in
default_parent, it will use the location from the mirror option from
mgarepo.conf. 

If the current work is based in another URL, it will use default_parent.

Options:
    -h      Show this message

Examples:
    mgarepo switch
    mgarepo switch https://mirrors.localnetwork/svn/packages/
"""

def parse_options():
    parser = OptionParser(help=HELP)
    opts, args = parser.parse_args()
    if len(args):
        opts.mirrorurl = args[0]
    return opts

def main():
    do_command(parse_options, switch)
