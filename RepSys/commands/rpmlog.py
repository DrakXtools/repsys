#
# This program will convert the output of "svn log" to be suitable
# for usage in an rpm %changelog session.
#
from RepSys import Error, layout, disable_mirror
from RepSys.command import *
from RepSys.svn import SVN
from RepSys.log import get_changelog, split_spec_changelog
from io import StringIO
import getopt
import os
import sys

HELP = """\
Usage: repsys rpmlog [OPTIONS] REPPKGDIRURL

Prints the RPM changelog of a given package.

Options:
    -r REV   Collect logs from given revision to revision 0
    -n NUM   Output only last NUM entries
    -T FILE  %changelog template file to be used
    -o       Append old package changelog
    -p       Append changelog found in .spec file
    -s       Sort changelog entries, even from the old log
    -M       Do not use the mirror (use the main repository)
    -F       Do not use full name & email for packagers where available
    -h       Show this message

Examples:
    repsys rpmlog python
    repsys rpmlog svn://svn.mageia.org/svn/packages/cauldron/python/current
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.add_option("-r", dest="revision")
    parser.add_option("-n", dest="size", type="int")
    parser.add_option("-T", "--template", dest="template", type="string")
    parser.add_option("-o", dest="oldlog", default=False,
            action="store_true")
    parser.add_option("-p", dest="usespec", default=False,
            action="store_true")
    parser.add_option("-s", dest="sort", default=False,
            action="store_true")
    parser.add_option("-M", "--no-mirror", action="callback",
            callback=disable_mirror)
    parser.add_option("-F", dest="fullnames", default=True,
            action="store_false")
    opts, args = parser.parse_args()
    if len(args) != 1:
        raise Error("invalid arguments")
    opts.pkgdirurl = layout.package_url(args[0])
    return opts

def rpmlog(pkgdirurl, revision, size, template, oldlog, usespec, sort, fullnames):
    another = None
    if usespec:
        svn = SVN()
        specurl = layout.package_spec_url(pkgdirurl)
        rawspec = svn.cat(specurl, rev=revision)
        spec, another = split_spec_changelog(StringIO(rawspec))
    newlog = get_changelog(pkgdirurl, another=another, rev=revision,
            size=size, sort=sort, template=template, oldlog=oldlog, fullnames=fullnames)
    # make sure stdout support unicode, otherwise it'll croak when encountered
    if not "UTF-8" in sys.stdout.encoding:
        sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="UTF-8")
    sys.stdout.writelines(newlog)

def main():
    do_command(parse_options, rpmlog)

# vim:sw=4:ts=4:et
