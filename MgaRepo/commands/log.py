from MgaRepo import config, mirror, disable_mirror
from MgaRepo.command import *
from MgaRepo.layout import package_url, checkout_url
from MgaRepo.rpmutil import sync
from MgaRepo.util import execcmd
import sys
import os
import subprocess
import shlex

HELP = """\
Usage: mgarepo log [OPTIONS] [PACKAGE]

Shows the SVN log for a given package.

Options:
    -h           Show this message
    -v           Show changed paths
    -l LIMIT     Limit of log entries to show    
    -r REV       Show a specific revision
    -M           Do not use the mirror (use the main repository)
    -s           Show release path       

Examples:
    mgarepo log mutt
    mgarepo log 2009.1/mutt
"""

def parse_options():
    parser = OptionParser(help=HELP)
    parser.add_option("-v", dest="verbose", action="store_true",
            default=False)
    parser.add_option("-l", "--limit", dest="limit", type="int",
            default=None)
    parser.add_option("-r", dest="revision", type="string", default=None)
    parser.add_option("-M", "--no-mirror", action="callback",
            callback=disable_mirror)
    parser.add_option("-s", dest="releases", action="store_true",
            default=False)
    opts, args = parser.parse_args()
    if len(args):
        opts.pkgdirurl = package_url(args[0])
    else:
        parser.error("log requires a package name")
    return opts

def svn_log(pkgdirurl, verbose=False, limit=None, revision=None, releases=None):
    mirror.info(pkgdirurl)
    url = checkout_url(pkgdirurl, releases=releases)
    svncmd = config.get("global", "svn-command", "svn")
    args = [svncmd, "log", url]
    if verbose:
        args.append("-v")
    if limit:
        args.append("-l")
        args.append(limit)
    if revision:
        args.append("-r")
        args.append(revision)
    if os.isatty(sys.stdin.fileno()):
        pager = shlex.split(os.environ.get("PAGER", "less"))
        p = subprocess.Popen(args, stdout=subprocess.PIPE)
        p2 = subprocess.Popen(pager, stdin=p.stdout)
        p2.wait()
        p.wait()
    else:
        execcmd(args, show=True)

def main():
    do_command(parse_options, svn_log)
