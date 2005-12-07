#!/usr/bin/python
from RepSys import Error, config
from RepSys.svn import SVN
import tempfile
import shutil
import time
import os

def svn2rpm(pkgdirurl, rev=None, size=None):
    concat = config.get("log", "concat", "").split()
    svn = SVN()
    log = svn.log(os.path.join(pkgdirurl, "current"), start=rev)
    if (size is not None):
        log = log[:size]
    rpmlog = []
    lastauthor = None
    for logentry in log:
        entryheader = []
        if lastauthor != logentry.author or \
           not (logentry.author in concat or "*" in concat):
            entryheader.append(time.strftime("* %a %b %d %Y ", logentry.date))
            entryheader.append(config.get("users", logentry.author,
                               logentry.author))
            entryheader.append("\n")
            entryheader.append(time.strftime("+ %Y-%m-%d %H:%M:%S",
                               logentry.date))
            entryheader.append(" (%d)" % logentry.revision)
            if lastauthor:
                rpmlog.append("")
            lastauthor = logentry.author
            entrylines = []
        first = 1
        for line in logentry.lines:
            if line:
                line = line.replace("%", "%%")
                if first:
                    first = 0
                    if entryheader:
                        rpmlog.append("".join(entryheader))
                    line = line.lstrip()
                    if line[0] != "-":
                        nextline = "- " + line
                    else:
                        nextline = line
                elif line[0] != " " and line[0] != "-":
                    nextline = "  " + line
                else:
                    nextline = line
                if nextline not in entrylines:
                    rpmlog.append(nextline)
                    entrylines.append(nextline)
    return "\n".join(rpmlog)+"\n"

def specfile_svn2rpm(pkgdirurl, specfile, rev=None, size=None):
    file = open(specfile)
    lines = file.readlines()
    file.close()
    newlines = []
    found = 0
    
    # Strip old changelogs
    for line in lines:
        if line.startswith("%changelog"):
            found = 1
        elif not found:
            newlines.append(line)
        elif line.startswith("%"):
            found = 0
            newlines.append(line)

    # Create new changelog
    newlines.append("\n\n%changelog\n")
    newlines.append(svn2rpm(pkgdirurl, rev, size))

    # Merge old changelog, if available
    oldurl = config.get("log", "oldurl")
    if oldurl:
        svn = SVN()
        tmpdir = tempfile.mktemp()
        try:
            pkgname = os.path.basename(pkgdirurl)
            pkgoldurl = os.path.join(oldurl, pkgname)
            if svn.ls(pkgoldurl, noerror=1):
                svn.checkout(pkgoldurl, tmpdir, rev=rev)
                logfile = os.path.join(tmpdir, "log")
                if os.path.isfile(logfile):
                    file = open(logfile)
                    newlines.append("\n")
                    newlines.append(file.read())
                    file.close()
        finally:
            if os.path.isdir(tmpdir):
                shutil.rmtree(tmpdir)

    # Write new specfile
    file = open(specfile, "w")
    file.writelines(newlines)
    file.close()

# vim:et:ts=4:sw=4
