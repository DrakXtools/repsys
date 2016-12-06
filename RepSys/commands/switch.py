from RepSys.command import *
from RepSys.rpmutil import switch

HELP = """\
Usage: repsys switch [URL]

Relocates the working copy to the base location URL.

If URL is not provided, it will use the option repository from repsys.conf
as default, or, if the current working copy is already based in
default_parent, it will use the location from the mirror option from
repsys.conf. 

If the current work is based in another URL, it will use default_parent.

Options:
    -h      Show this message

Examples:
    repsys switch
    repsys switch https://mirrors.localnetwork/svn/packages/
"""

def parse_options():
    parser = OptionParser(help=HELP)
    opts, args = parser.parse_args()
    if len(args):
        opts.mirrorurl = args[0]
    return opts

def main():
    do_command(parse_options, switch)
