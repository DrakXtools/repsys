from RepSys import Error
from RepSys.command import *
from RepSys.rpmutil import binrepo_delete

HELP = """\
Usage: repsys del [OPTIONS] [PATH]

Remove a given file from the binary sources repository.

Changes in the sources file will be left uncommited.

Options:
    -c      automatically commit the 'sources' file
    -h      help

"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.add_option("-c", dest="commit", default=False,
            action="store_true")
    opts, args = parser.parse_args()
    if len(args):
        opts.paths = args
    else:
        raise Error, "you need to provide a path"
    return opts

def main():
    do_command(parse_options, binrepo_delete)
