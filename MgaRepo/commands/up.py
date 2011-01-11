from MgaRepo import Error
from MgaRepo.command import *
from MgaRepo.rpmutil import update

HELP = """\
Usage: mgarepo up [PATH]

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
