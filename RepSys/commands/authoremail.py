#!/usr/bin/python
from RepSys import Error, config
from RepSys.command import *
import sys
import getopt

HELP = """\
Usage: repsys authoremail [OPTIONS] AUTHOR

Shows the e-mail of an SVN author. It is just a simple interface to access
the [authors] section of repsys.conf.

Options:
    -h      Show this message

Examples:
    repsys authoremail john
"""

def parse_options():
    parser = OptionParser(help=HELP)
    opts, args = parser.parse_args()
    if len(args) != 1:
        raise Error, "invalid arguments"
    opts.author = args[0]
    return opts

def print_author_email(author):
    email = config.get("users", author)
    if not email:
        raise Error, "author not found"
    print email
    
def main():
    do_command(parse_options, print_author_email)

# vim:et:ts=4:sw=4
