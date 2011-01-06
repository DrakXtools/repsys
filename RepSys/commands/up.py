from RepSys import Error
from RepSys.command import *
from RepSys.rpmutil import update

HELP = """\
Usage: repsys up [PATH]

Update the package working copy and synchronize all binaries.

Options:
    -h      help
"""

def parse_options():
    parser = OptionParser(help=HELP)
    opts, args = parser.parse_args()
    if args:
        opts.target = args[0]
    return opts

def main():
    do_command(parse_options, update)
