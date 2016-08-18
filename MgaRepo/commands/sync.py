from MgaRepo.command import *
from MgaRepo.rpmutil import sync

HELP = """\
Usage: mgarepo sync

Will add or remove from the working copy those files added or removed
in the spec file.

It will not commit the changes.

Options:
    --dry-run    Print results without changing the working copy
    --download -d
                 Try to download the source files not found
    -h           Show this message

Examples:
    mgarepo sync
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.add_option("--dry-run", dest="dryrun", default=False,
            action="store_true")
    # TODO:
    # Completely remove -c switch from code
    parser.add_option("-c", dest="commit", default=False,
            action="store_true")
    parser.add_option("-d", "--download", dest="download", default=False,
            action="store_true")
    opts, args = parser.parse_args()
    # TODO:
    # Completely remove -c switch from code
    if opts.commit:
        parser.error("Option -c is deprecated and should not be used anymore!")
    if len(args):
        opts.target = args[0]
    return opts

def main():
    do_command(parse_options, sync)
