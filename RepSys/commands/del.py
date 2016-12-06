from RepSys import Error
from RepSys.command import *
from RepSys.rpmutil import delete

HELP = """\
Usage: repsys del [OPTIONS] [PATH]

Remove a given file from the binary sources repository.

Options:
    -h      help

"""

def parse_options():
    parser = OptionParser(help=HELP)
    opts, args = parser.parse_args()
    if len(args):
        opts.paths = args
    else:
        raise Error("you need to provide a path")
    return opts

def main():
    do_command(parse_options, delete)
