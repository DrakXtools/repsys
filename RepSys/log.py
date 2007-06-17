#!/usr/bin/python
from RepSys import Error, config, RepSysTree
from RepSys.svn import SVN
from RepSys.util import execcmd

try:
    from Cheetah.Template import Template
except ImportError:
    raise Error, "repsys requires the package python-cheetah"

import sys
import os
import re
import time
import locale
import glob
import tempfile
import shutil


locale.setlocale(locale.LC_ALL, "C")

default_template = """
#for $rel in $releases_by_author
* $rel.date $rel.author_name <$rel.author_email> $rel.version-$rel.release
 ##
 #if not $rel.released
  (not released yet)
 #end if
 #for $rev in $rel.release_revisions
  #for $line in $rev.lines
  $line
  #end for
 #end for

 #for $author in $rel.authors
  + $author.name <$author.email>
  #for $rev in $author.revisions
    #for $line in $rev.lines
    $line
    #end for
  #end for

 #end for
#end for
"""

def getrelease(pkgdirurl, rev=None, macros=[], exported=None):
    """Tries to obtain the version-release of the package for a 
    yet-not-markrelease revision of the package.

    Is here where things should be changed if "automatic release increasing" 
    will be used.
    """
    from RepSys.rpmutil import rpm_macros_defs
    svn = SVN(baseurl=pkgdirurl)
    pkgcurrenturl = os.path.join(pkgdirurl, "current")
    specurl = os.path.join(pkgcurrenturl, "SPECS")
    if exported is None:
        tmpdir = tempfile.mktemp()
        svn.export(specurl, tmpdir, rev=rev)
    else:
        tmpdir = os.path.join(exported, "SPECS")
    try:
        found = glob.glob(os.path.join(tmpdir, "*.spec"))
        if not found:
            raise Error, "no .spec file found inside %s" % specurl
        specpath = found[0]
        options = rpm_macros_defs(macros)
        command = (("rpm -q --qf '%%{EPOCH}:%%{VERSION}-%%{RELEASE}\n' "
                   "--specfile %s %s 2>/dev/null") % 
                   (specpath, options))
        status, output = execcmd(command)
        if status != 0:
            raise Error, "Error in command %s: %s" % (command, output)
        releases = output.split()
        try:
            epoch, vr = releases[0].split(":", 1)
            version, release = vr.split("-", 1)
        except ValueError:
            raise Error, "Invalid command output: %s: %s" % \
                    (command, output)
        #XXX check if this is the right way:
        if epoch == "(none)":
            ev = version
        else:
            ev = epoch + ":" + version
        return ev, release
    finally:
        if exported is None and os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)
            
class _Revision:
    lines = []
    date = None
    raw_date = None
    revision = None
    author_name = None
    author_email = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        lines = repr(self.lines)[:30] + "...]" 
        line = "<_Revision %d author=%r date=%r lines=%s>" % \
                    (self.revision, self.author, self.date, lines)
        return line


class _Release(_Revision):
    version = None
    release = None
    revisions = []
    release_revisions = []
    authors = []
    visible = False

    def __init__(self, **kwargs):
        self.revisions = []
        _Revision.__init__(self, **kwargs)

    def __repr__(self):
        line = "<_Release v=%s r=%s revs=%r>" % \
                    (self.version, self.release, self.revisions)
        return line

unescaped_macro_pat = re.compile(r"([^%])%([^%])")

def escape_macros(text):
    escaped = unescaped_macro_pat.sub("\\1%%\\2", text)
    return escaped

def format_lines(lines):
    first = 1
    entrylines = []
    perexpr = re.compile(r"([^%])%([^%])")
    for line in lines:
        if line:
            line = escape_macros(line)
            if first:
                first = 0
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
                entrylines.append(nextline)
    return entrylines


class _Author:
    name = None
    email = None
    revisions = None


def group_releases_by_author(releases):
    allauthors = []
    grouped = []
    for release in releases:
        authors = {}
        latest = None
        for revision in release.revisions:
            authors.setdefault(revision.author, []).append(revision)

        # all the mess below is to sort by author and by revision number
        decorated = []
        for authorname, revs in authors.iteritems():
            author = _Author()
            author.name = revs[0].author_name
            author.email = revs[0].author_email
            revdeco = [(r.revision, r) for r in revs]
            revdeco.sort(reverse=1)
            author.revisions = [t[1] for t in revdeco]
            revlatest = author.revisions[0]
            # keep the latest revision even for silented authors (below)
            if latest is None or revlatest.revision > latest.revision:
                latest = revlatest
            count = sum(len(rev.lines) for rev in author.revisions)
            if count == 0:
                # skipping author with only silented lines
                continue
            decorated.append((revdeco[0][0], author))

        if not decorated:
            # skipping release with only authors with silented lines
            continue

        decorated.sort(reverse=1)
        release.authors = [t[1] for t in decorated]
        # the difference between a released and a not released _Release is
        # the way the release numbers is obtained. So, when this is a
        # released, we already have it, but if we don't, we should get de
        # version/release string using getrelease and then get the first
        first, release.authors = release.authors[0], release.authors[1:]
        release.author_name = first.name
        release.author_email = first.email
        release.release_revisions = first.revisions

        #release.date = first.revisions[0].date
        release.date = latest.date
        release.raw_date = latest.raw_date
        #release.revision = first.revisions[0].revision
        release.revision = latest.revision

        grouped.append(release)

    return grouped


def group_revisions_by_author(currentlog):
    revisions = []
    last_author = None
    for entry in currentlog:
        revision = _Revision()
        revision.lines = format_lines(entry.lines)
        revision.raw_date = entry.date
        revision.date = parse_raw_date(entry.date)
        revision.revision = entry.revision
        if entry.author == last_author:
            revisions[-1].revisions.append(revision)
        else:
            author = _Author()
            author.name, author.email = get_author_name(entry.author)
            author.revisions = [revision]
            revisions.append(author)
        last_author = entry.author
    return revisions


emailpat = re.compile("(?P<name>.*?)\s*<(?P<email>.*?)>")

def get_author_name(author):
    found = emailpat.match(config.get("users", author, author))
    name = ((found and found.group("name")) or author)
    email = ((found and found.group("email")) or author)
    return name, email

def parse_raw_date(rawdate):
    return time.strftime("%a %b %d %Y", rawdate)

def filter_log_lines(lines):
    # lines in commit messages containing SILENT at any position will be
    # skipped; commits with their log messages beggining with SILENT in the
    # first positionj of the first line will have all lines ignored.
    ignstr = config.get("log", "ignore-string", "SILENT")
    if len(lines) and lines[0].startswith(ignstr):
        return []
    filtered = [line for line in lines if ignstr not in line]
    return filtered


def make_release(author=None, revision=None, date=None, lines=None,
        entries=[], released=True, version=None, release=None):
    rel = _Release()
    rel.author = author
    if author:
        rel.author_name, rel.author_email = get_author_name(author)
    rel.revision = revision
    rel.version = version
    rel.release = release
    rel.date = (date and parse_raw_date(date)) or None
    rel.lines = lines
    rel.released = released
    rel.visible = False
    for entry in entries:
        lines = filter_log_lines(entry.lines)
        if lines:
            rel.visible = True
        revision = _Revision()
        revision.revision = entry.revision
        revision.lines = format_lines(lines)
        revision.date = parse_raw_date(entry.date)
        revision.raw_date = entry.date
        revision.author = entry.author
        (revision.author_name, revision.author_email) = \
                get_author_name(entry.author)
        rel.revisions.append(revision)
    return rel


def dump_file(releases, currentlog=None, template=None):
    templpath = template or config.get("template", "path", None)
    params = {}
    if templpath is None or not os.path.exists(templpath):
        params["source"] = default_template
        sys.stderr.write("warning: %s not found. using built-in template.\n"%
                templpath)
    else:
        params["file"] = templpath
    releases_author = group_releases_by_author(releases)
    revisions_author = group_revisions_by_author(currentlog)
    params["searchList"] = [{"releases_by_author" : releases_author,
                             "releases" : releases,
                             "revisions_by_author": revisions_author}]
    t = Template(**params)
    return t.respond()


class InvalidEntryError(Exception):
    pass

def parse_repsys_entry(revlog):
    # parse entries in the format:
    # %repsys <operation>
    # key: value
    # ..
    # <newline>
    # <comments>
    #
    if len(revlog.lines) == 0 or not revlog.lines[0].startswith("%repsys"):
        raise InvalidEntryError
    try:       
        data = {"operation" : revlog.lines[0].split()[1]}
    except IndexError:
        raise InvalidEntryError
    for line in revlog.lines[1:]:
        if not line:
            break
        try:
            key, value = line.split(":", 1)
        except ValueError:
            raise InvalidEntryError
        data[key.strip().lower()] = value.strip() # ???
    return data
        

def get_revision_offset():
    try:
        revoffset = config.getint("log", "revision-offset", 0)
    except (ValueError, TypeError):
        raise Error, ("Invalid revision-offset number in configuration "
                      "file(s).")
    return revoffset or 0

oldmsgpat = re.compile(
        r"Copying release (?P<rel>[^\s]+) to (?P<dir>[^\s]+) directory\.")

def parse_markrelease_log(relentry):
    if not ((relentry.lines and oldmsgpat.match(relentry.lines[0]) \
            or parse_repsys_entry(relentry))):
        raise InvalidEntryError
    from_rev = None
    path = None
    for changed in relentry.changed:
        if changed["action"] == "A" and changed["from_rev"]:
            from_rev = changed["from_rev"]
            path = changed["path"]
            break
    else:
        raise InvalidEntryError
    # get the version and release from the names in the path, do not relay
    # on log messages
    version, release = path.rsplit(os.path.sep, 3)[-2:]
    return version, release, from_rev


def svn2rpm(pkgdirurl, rev=None, size=None, submit=False,
        template=None, macros=[], exported=None):
    concat = config.get("log", "concat", "").split()
    revoffset = get_revision_offset()
    svn = SVN(baseurl=pkgdirurl)
    pkgreleasesurl = os.path.join(pkgdirurl, "releases")
    pkgcurrenturl = os.path.join(pkgdirurl, "current")
    releaseslog = svn.log(pkgreleasesurl, noerror=1)
    currentlog = svn.log(pkgcurrenturl, limit=size, start=rev,
            end=revoffset)

    # sort releases by copyfrom-revision, so that markreleases for same
    # revisions won't look empty
    releasesdata = []
    if releaseslog:
        for relentry in releaseslog[::-1]:
            try:
                (version, release, relrevision) = \
                        parse_markrelease_log(relentry)
            except InvalidEntryError:
                continue
            releasesdata.append((relrevision, -relentry.revision, relentry, 
                version, release))
        releasesdata.sort()

    # collect valid releases using the versions provided by the changes and
    # the packages
    prevrevision = 0
    releases = []
    for (relrevision, dummy, relentry, version, release) in releasesdata:
        if prevrevision == relrevision: 
            # ignore older markrelease of the same revision, since they
            # will have no history
            continue
        entries = [entry for entry in currentlog
                    if relrevision >= entry.revision and
                      (prevrevision < entry.revision)]
        if not entries:
            #XXX probably a forced release, without commits in current/,
            # check if this is the right behavior
            sys.stderr.write("warning: skipping (possible) release "
                    "%s-%s@%s, no commits since previous markrelease (r%r)\n" %
                    (version, release, relrevision, prevrevision))
            continue

        release = make_release(author=relentry.author,
                revision=relentry.revision, date=relentry.date,
                lines=relentry.lines, entries=entries,
                version=version, release=release)
        releases.append(release)
        prevrevision = relrevision
            
    # look for commits that have been not submited (released) yet
    # this is done by getting all log entries newer (revision larger)
    # than releaseslog[0] (in the case it exists)
    if releaseslog:
        latest_revision = releaseslog[0].revision
    else:
        latest_revision = 0
    notsubmitted = [entry for entry in currentlog 
                    if entry.revision > latest_revision]
    if notsubmitted:
        # if they are not submitted yet, what we have to do is to add
        # a release/version number from getrelease()
        version, release = getrelease(pkgdirurl, macros=macros,
                exported=exported)
        toprelease = make_release(entries=notsubmitted, released=False,
                        version=version, release=release)
        releases.append(toprelease)

    data = dump_file(releases[::-1], currentlog=currentlog, template=template)
    return data



def specfile_svn2rpm(pkgdirurl, specfile, rev=None, size=None,
        submit=False, template=None, macros=[], exported=None):
    newlines = []
    found = 0
    
    # Strip old changelogs
    for line in open(specfile):
        if line.startswith("%changelog"):
            found = 1
        elif not found:
            newlines.append(line)
        elif line.startswith("%"):
            found = 0
            newlines.append(line)

    # Create new changelog
    newlines.append("\n\n%changelog\n")
    newlines.append(svn2rpm(pkgdirurl, rev=rev, size=size, submit=submit,
        template=template, macros=macros, exported=exported))

    # Merge old changelog, if available
    oldurl = config.get("log", "oldurl")
    if oldurl:
        svn = SVN(baseurl=pkgdirurl)
        tmpdir = tempfile.mktemp()
        try:
            pkgname = RepSysTree.pkgname(pkgdirurl)
            pkgoldurl = os.path.join(oldurl, pkgname)
            try:
                # we're using HEAD here because fixes in misc/ (oldurl) may
                # be newer than packages' last changed revision.
                svn.export(pkgoldurl, tmpdir)
            except Error:
                pass
            else:
                logfile = os.path.join(tmpdir, "log")
                if os.path.isfile(logfile):
                    file = open(logfile)
                    newlines.append("\n")
                    log = file.read()
                    log = escape_macros(log)
                    newlines.append(log)
                    file.close()
        finally:
            if os.path.isdir(tmpdir):
                shutil.rmtree(tmpdir)

    # Write new specfile
    file = open(specfile, "w")
    file.write("".join(newlines))
    file.close()


if __name__ == "__main__":
    l = svn2rpm(sys.argv[1])
    print l

# vim:et:ts=4:sw=4
