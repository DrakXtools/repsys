#!/usr/bin/python3
from MgaRepo import Error, config, layout
from MgaRepo.svn import SVN
from MgaRepo.util import execcmd

from io import StringIO

import sys
import os
import re
import time
import locale
import glob
import tempfile
import shutil
import subprocess


locale.setlocale(locale.LC_ALL, "C")

def getrelease(pkgdirurl, rev=None, macros=[], exported=None):
    """Tries to obtain the version-release of the package for a 
    yet-not-markrelease revision of the package.

    Is here where things should be changed if "automatic release increasing" 
    will be used.
    """
    from MgaRepo.rpmutil import rpm_macros_defs
    svn = SVN()
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
            raise Error("no .spec file found inside %s" % specurl)
        specpath = found[0]
        options = rpm_macros_defs(macros)
        command = (("rpm -q --qf '%%{EPOCH}:%%{VERSION}-%%{RELEASE}\n' "
                   "--specfile %s %s") %
                   (specpath, options))
        pipe = subprocess.Popen(command, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, shell=True)
        pipe.wait()
        output = pipe.stdout.read()
        error = pipe.stderr.read()
        if pipe.returncode != 0:
            raise Error("Error in command %s: %s" % (command, error))
        releases = output.split()
        try:
            epoch, vr = releases[0].split(":", 1)
            version, release = vr.split("-", 1)
        except ValueError:
            raise Error("Invalid command output: %s: %s" % \
                    (command, output))
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

unescaped_macro_pat = re.compile(r"(^|[^%])%([^%])")

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
    visible = False


def group_releases_by_author(releases):
    allauthors = []
    grouped = []
    for release in releases:

        # group revisions of the release by author
        authors = {}
        latest = None
        for revision in release.revisions:
            authors.setdefault(revision.author, []).append(revision)

        # create _Authors and sort them by their latest revisions
        decorated = []
        for authorname, revs in authors.items():
            author = _Author()
            author.name = revs[0].author_name
            author.email = revs[0].author_email
            author.revisions = revs
            # #41117: mark those authors without visible messages
            author.visible = bool(sum(len(rev.lines) for rev in revs))
            revlatest = author.revisions[0]
            # keep the latest revision even for completely invisible
            # authors (below)
            if latest is None or revlatest.revision > latest.revision:
                latest = revlatest
            if not author.visible:
                # only sort those visible authors, invisible ones are used
                # only in "latest"
                continue
            decorated.append((revlatest.revision, author))
        decorated.sort(reverse=1)

        if release.visible:
            release.authors = [t[1] for t in decorated]
            firstrel, release.authors = release.authors[0], release.authors[1:]
            release.author_name = firstrel.name
            release.author_email = firstrel.email
            release.release_revisions = firstrel.revisions
        else:
            # we don't care about other possible authors in completely
            # invisible releases
            firstrev = release.revisions[0]
            release.author_name = firstrev.author_name
            release.author_email = firstrev.author_email
            release.raw_date = firstrev.raw_date
            release.date = firstrev.date

        release.date = latest.date
        release.raw_date = latest.raw_date
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
    # Lines in commit messages beginning with CLOG will be the only shown
    # in the changelog. These lines will have the CLOG token and blanks
    # stripped from the beginning.
    onlylines = None
    clogstr = config.get("log", "unignore-string")
    if clogstr:
        clogre = re.compile(r"(^%s[^ \t]?[ \t])" % clogstr)
        onlylines = [clogre.sub("", line)
                for line in lines if line.startswith(clogstr)]
    if onlylines:
        filtered = onlylines
    else:
        # Lines in commit messages containing SILENT at any position will be
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
        revision = _Revision()
        revision.revision = entry.revision
        revision.lines = format_lines(lines)
        if revision.lines:
            rel.visible = True
        revision.date = parse_raw_date(entry.date)
        revision.raw_date = entry.date
        revision.author = entry.author
        (revision.author_name, revision.author_email) = \
                get_author_name(entry.author)
        rel.revisions.append(revision)
    return rel


def dump_file(releases, currentlog=None, template=None):
    ''' Template cheetah suppressed and replaced by hard code. The template is selectable with the "name" in "template" section of config file.'''
    templname = template or config.get("template", "name",
            "default")
    draft=""
    releases_author = group_releases_by_author(releases)
    revisions_author = group_revisions_by_author(currentlog)
    if templname == 'revno':
        ''' a specific template'''
        for rel in releases_author:
            if not rel.released: 
                draft = "  (not released yet)\n"
            draft = draft + "* {0} {1} <{2}> {3}-{4}\n\n".format(rel.date, rel.author_name, rel.author_email, rel.version, rel.release)
            for rev in rel.release_revisions:
                    first=True
                    spaces = " " * (len(str(rev.revision)) +3)
                    for line in rev.lines:
                        if first:
                            draft = draft +"[{0}] {1}\n".format(rev.revision, line)
                            first = False
                        else:
                            draft = draft + spaces + line + "\n"
            for author in rel.authors:
                if not author.visible:
                    continue
                draft += "+ {0} <{1}>\n".format(author.name, author.email)
                for rev in author.revisions:
                    first=True
                    spaces = " " * (len(str(rev.revision)) + 3)
                    for line in rev.lines:
                        if first:
                            draft = draft +"[{0}] {1}\n".format(rev.revision, line)
                            first = False
                        else:
                            draft = draft + spaces + line + "\n"
    else:
        #  default template
        if not releases_author[-1].visible:
            releases_author = releases_author[:-1]
        for rel in releases_author:
            if not rel.released: 
                draft = "  (not released yet)\n"
            draft = draft + "* {0} {1} <{2}> {3}-{4}\n+ Revision: {5}\n".format(rel.date, rel.author_name, rel.author_email, rel.version, rel.release, rel.revision)
            if not rel.visible:
                draft = draft + "+ rebuild (emptylog)\n"
            for rev in rel.release_revisions:
                for line in rev.lines:
                    draft = draft + line + "\n"
            for author in rel.authors:
                if not author.visible:
                    continue
                draft += "+ {0} <{1}>\n".format(author.name, author.email)
                for rev in author.revisions:
                    for line in rev.lines:
                        draft = draft + line + "\n"
            draft += "\n"
            draft += "\n"
    return draft

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
        raise Error("Invalid revision-offset number in configuration "
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
    svn = SVN()
    pkgreleasesurl = layout.checkout_url(pkgdirurl, releases=True)
    pkgcurrenturl = layout.checkout_url(pkgdirurl)
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
            
    # look for commits that have been not submitted (released) yet
    # this is done by getting all log entries newer (greater revision no.)
    # than releasesdata[-1] (in the case it exists)
    if releasesdata:
        latest_revision = releasesdata[-1][0] # the latest copied rev
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

def _split_changelog(stream):
    current = None
    count = 0
    def finish(entry):
        lines = entry[2]
        # strip newlines at the end
        for i in range(len(lines)-1, -1, -1):
            if lines[i] != "\n":
                break
            del lines[i]
        return entry
    for line in stream:
        if line.startswith("*"):
            if current:
                yield finish(current)
            fields = line.split()
            rawdate = " ".join(fields[:5])
            try:
                date = time.strptime(rawdate, "* %a %b %d %Y")
            except ValueError as e:
                raise Error("failed to parse spec changelog: %s" % e)
            curlines = [line]
            current = (date, count, curlines)
            # count used to ensure stable sorting when changelog entries
            # have the same date, otherwise it would also compare the
            # changelog lines
            count -= 1
        elif current:
            curlines.append(line)
        else:
            pass # not good, but ignore
    if current:
        yield finish(current)

def sort_changelog(stream):
    entries = _split_changelog(stream)
    log = StringIO()
    for time, count, elines in sorted(entries, reverse=True):
        log.writelines(elines)
        log.write("\n")
    return log

def split_spec_changelog(stream):
    chlog = StringIO()
    spec = StringIO()
    found = 0
    visible = 0
    for line in stream:
        if line.startswith("%changelog"):
            found = 1
        elif not found:
            spec.write(line)
        elif found:
            if line.strip():
                visible = 1
            chlog.write(line)
        elif line.startswith("%"):
            found = 0
            spec.write(line)
    spec.seek(0)
    if not visible:
        # when there are only blanks in the changelog, make it empty
        chlog = StringIO()
    return spec, chlog

def get_old_log(pkgdirurl):
    chlog = StringIO()
    oldurl = config.get("log", "oldurl")
    if oldurl:
        svn = SVN()
        tmpdir = tempfile.mktemp()
        try:
            if oldurl == '.' or oldurl.startswith('./'):
                pkgoldurl = os.path.join(pkgdirurl, oldurl)
            else:
                pkgname = layout.package_name(pkgdirurl)
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
                    chlog.write("\n") # TODO needed?
                    log = file.read()
                    log = escape_macros(log)
                    chlog.write(log)
                    file.close()
        finally:
            if os.path.isdir(tmpdir):
                shutil.rmtree(tmpdir)
    chlog.seek(0)
    return chlog

def get_changelog(pkgdirurl, another=None, svn=True, rev=None, size=None,
        submit=False, sort=False, template=None, macros=[], exported=None,
        oldlog=False):
    """Generates the changelog for a given package URL

    @another:   a stream with the contents of a changelog to be merged with
                the one generated
    @svn:       enable changelog from svn
    @rev:       generate the changelog with the changes up to the given
                revision
    @size:      the number of revisions to be used (as in svn log --limit)
    @submit:    defines whether the latest unreleased log entries should have
                the version parsed from the spec file
    @sort:      should changelog entries be reparsed and sorted after appending
                the oldlog?
    @template:  the path to the cheetah template used to generate the
                changelog from svn
    @macros:    a list of tuples containing macros to be defined when
                parsing the version in the changelog
    @exported:  the path of a directory containing an already existing
                checkout of the package, so that the spec file can be
                parsed from there
    @oldlog:    if set it will try to append the old changelog file defined
                in oldurl in mgarepo.conf
    """
    newlog = StringIO()
    if svn:
        rawsvnlog = svn2rpm(pkgdirurl, rev=rev, size=size, submit=submit,
                template=template, macros=macros, exported=exported)
        newlog.write(rawsvnlog)
    if another:
        newlog.writelines(another)
    if oldlog:
        newlog.writelines(get_old_log(pkgdirurl))
    if sort:
        newlog.seek(0)
        newlog = sort_changelog(newlog)
    newlog.seek(0)
    return newlog

def specfile_svn2rpm(pkgdirurl, specfile, rev=None, size=None,
        submit=False, sort=False, template=None, macros=[], exported=None):
    with open(specfile, encoding = 'utf-8') as fi:
        spec, oldchlog = split_spec_changelog(fi)
    another = None
    if config.getbool("log", "merge-spec", False):
        another = oldchlog
    sort = sort or config.getbool("log", "sort", False)
    chlog = get_changelog(pkgdirurl, another=another, rev=rev, size=size,
                submit=submit, sort=sort, template=template, macros=macros,
                exported=exported, oldlog=True)
    print(spec)
    with open(specfile, "w", encoding='utf-8') as fo:
        fo.writelines(spec)
        fo.write("\n\n%changelog\n")
        fo.writelines(chlog)
 
if __name__ == "__main__":
    l = svn2rpm(sys.argv[1])
    print(l)

# vim:et:ts=4:sw=4
