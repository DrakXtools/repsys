from MgaRepo import Error, config, mirror, layout
from MgaRepo.util import execcmd, rellink
from MgaRepo.svn import SVN

import sys
import os
import string
import stat
import shutil
import re
import tempfile
import hashlib
import urlparse
import threading
from cStringIO import StringIO

DEFAULT_TARBALLS_REPO = "/tarballs"
BINARIES_DIR_NAME = "SOURCES"
BINARIES_CHECKOUT_NAME = "SOURCES-bin"

PROP_BINREPO_REV = "binrepo-rev"

BINREPOS_SECTION = "binrepos"

SOURCES_FILE = "sha1.lst"

class ChecksumError(Error):
    pass

def svn_baseurl(target):
    svn = SVN()
    info = svn.info2(target)
    if info is None:
        # unversioned resource
        newtarget = os.path.dirname(target)
        info = svn.info2(newtarget)
        assert info is not None, "svn_basedir should not be used with a "\
                "non-versioned directory"
    root = info["Repository Root"]
    url = info["URL"]
    kind = info["Node Kind"]
    path = url[len(root):]
    if kind == "directory":
        return url
    basepath = os.path.dirname(path)
    baseurl = mirror.normalize_path(url + "/" + basepath)
    return baseurl

def svn_root(target):
    svn = SVN()
    info = svn.info2(target)
    if info is None:
        newtarget = os.path.dirname(target)
        info = svn.info2(newtarget)
        assert info is not None
    return info["Repository Root"]

def enabled(url):
    use = config.getbool("global", "use-binaries-repository", False)
    return use

def default_repo():
    base = config.get("global", "binaries-repository", None)
    if base is None:
        default_parent = config.get("global", "default_parent", None)
        if default_parent is None:
            raise Error, "no binaries-repository nor default_parent "\
                    "configured"
        comps = urlparse.urlparse(default_parent)
        base = comps[1] + ":" + DEFAULT_TARBALLS_REPO
    return base

def translate_url(url):
    url = mirror.normalize_path(url)
    main = mirror.normalize_path(layout.repository_url())
    subpath = url[len(main)+1:]
    # [binrepos]
    # updates/2009.0 = svn+ssh://svn.mandriva.com/svn/binrepo/20090/
    ## svn+ssh://svn.mandriva.com/svn/packages/2009.0/trafshow/current
    ## would translate to 
    ## svn+ssh://svn.mandriva.com/svn/binrepo/20090/updates/trafshow/current/
    binbase = None
    if BINREPOS_SECTION in config.sections():
        for option, value in config.walk(BINREPOS_SECTION):
            if subpath.startswith(option):
                binbase = value
                break
    binurl = mirror._joinurl(binbase or default_repo(), subpath)
    return binurl

def translate_topdir(path):
    """Returns the URL in the binrepo from a given path inside a SVN
       checkout directory.

    @path: if specified, returns a URL in the binrepo whose path is the
           same as the path inside the main repository.
    """
    baseurl = svn_baseurl(path)
    binurl = translate_url(baseurl)
    target = mirror.normalize_path(binurl)
    return target

def is_binary(path):
    raw = config.get("binrepo", "upload-match",
            "\.(7z|Z|bin|bz2|cpio|db|deb|egg|gem|gz|jar|jisp|lzma|"\
               "pdf|pgn\\.gz|pk3|png|rpm|run|sdz|smzip|tar|tbz|"\
               "tbz2|tgz|ttf|uqm|wad|war|xar|xpi|xz|zip|wav|mp3|ogg|"\
	       "jpg|png|gif|avi|mpg|mpeg|rar)$")
    maxsize = config.getint("binrepo", "upload-match-size", "1048576") # 1MiB
    expr = re.compile(raw)
    name = os.path.basename(path)
    if expr.search(name):
        return True
    st = os.stat(path)
    if st[stat.ST_SIZE] >= maxsize:
        return True
    return False

def find_binaries(paths):
    new = []
    for path in paths:
        if os.path.isdir(path):
            for name in os.listdir(path):
                fpath = os.path.join(path, name)
                if is_binary(fpath):
                    new.append(fpath)
        else:
            if is_binary(path):
                new.append(path)
    return new

def make_symlinks(source, dest):
    todo = []
    tomove = []
    for name in os.listdir(source):
        path = os.path.join(source, name)
        if not os.path.isdir(path) and not name.startswith("."):
            destpath = os.path.join(dest, name)
            linkpath = rellink(path, destpath)
            if os.path.exists(destpath):
                if (os.path.islink(destpath) and
                        os.readlink(destpath) == linkpath):
                    continue
                movepath = destpath + ".repsys-moved"
                if os.path.exists(movepath):
                    raise Error, "cannot create symlink, %s already "\
                            "exists (%s too)" % (destpath, movepath)
                tomove.append((destpath, movepath))
            todo.append((destpath, linkpath))
    for destpath, movepath in tomove:
        os.rename(destpath, movepath)
    for destpath, linkpath in todo:
        os.symlink(linkpath, destpath)

def download(targetdir, pkgdirurl=None, export=False, show=True,
        revision=None, symlinks=True, check=False):
    assert not export or (export and pkgdirurl)
    svn = SVN()
    sourcespath = os.path.join(targetdir, "SOURCES")
    binpath = os.path.join(targetdir, BINARIES_CHECKOUT_NAME)
    if pkgdirurl:
        topurl = translate_url(pkgdirurl)
    else:
        topurl = translate_topdir(targetdir)
    binrev = None
    if revision:
        if pkgdirurl:
            binrev = mapped_revision(pkgdirurl, revision)
        else:
            binrev = mapped_revision(targetdir, revision, wc=True)
    binurl = mirror._joinurl(topurl, BINARIES_DIR_NAME)
    if export:
        svn.export(binurl, binpath, rev=binrev, show=show)
    else:
        svn.checkout(binurl, binpath, rev=binrev, show=show)
    if symlinks:
        make_symlinks(binpath, sourcespath)
    if check:
        check_sources(targetdir)

def import_binaries(topdir, pkgname):
    """Import all binaries from a given package checkout

    (with pending svn adds)

    @topdir: the path to the svn checkout
    """
    svn = SVN()
    topurl = translate_topdir(topdir)
    sourcesdir = os.path.join(topdir, "SOURCES")
    bintopdir = tempfile.mktemp("repsys")
    try:
        svn.checkout(topurl, bintopdir)
        checkout = True
    except Error:
        bintopdir = tempfile.mkdtemp("repsys")
        checkout = False
    try:
        bindir = os.path.join(bintopdir, BINARIES_DIR_NAME)
        if not os.path.exists(bindir):
            if checkout:
                svn.mkdir(bindir)
            else:
                os.mkdir(bindir)
        binaries = find_binaries([sourcesdir])
        update = update_sources_threaded(topdir, added=binaries)
        for path in binaries:
            name = os.path.basename(path)
            binpath = os.path.join(bindir, name)
            os.rename(path, binpath)
            try:
                svn.remove(path)
            except Error:
                # file not tracked
                svn.revert(path)
            if checkout:
                svn.add(binpath)
        log = "imported binaries for %s" % pkgname
        if checkout:
            rev = svn.commit(bindir, log=log)
        else:
            rev = svn.import_(bintopdir, topurl, log=log)
        svn.propset(PROP_BINREPO_REV, str(rev), topdir)
        update.join()
        svn.add(sources_path(topdir))
    finally:
        shutil.rmtree(bintopdir)

def create_package_dirs(bintopdir):
    svn = SVN()
    binurl = mirror._joinurl(bintopdir, BINARIES_DIR_NAME)
    silent = config.get("log", "ignore-string", "SILENT")
    message = "%s: created binrepo package structure" % silent
    svn.mkdir(binurl, log=message, parents=True)

def parse_sources(path):
    entries = {}
    f = open(path)
    for rawline in f:
        line = rawline.strip()
        try:
            sum, name = line.split(None, 1)
        except ValueError:
            # failed to unpack, line format error
            raise Error, "invalid line in sources file: %s" % rawline
        entries[name] = sum
    return entries

def check_hash(path, sum):
    newsum = file_hash(path)
    if newsum != sum:
        raise ChecksumError, "different checksums for %s: expected %s, "\
                "but %s was found" % (path, sum, newsum)

def check_sources(topdir):
    spath = sources_path(topdir)
    if not os.path.exists(spath):
        raise Error, "'%s' was not found" % spath
    entries = parse_sources(spath)
    for name, sum in entries.iteritems():
        fpath = os.path.join(topdir, "SOURCES", name)
        check_hash(fpath, sum)

def file_hash(path):
    sum = hashlib.sha1()
    f = open(path)
    while True:
        block = f.read(4096)
        if not block:
            break
        sum.update(block)
    f.close()
    return sum.hexdigest()

def sources_path(topdir):
    path = os.path.join(topdir, "SOURCES", SOURCES_FILE)
    return path

def update_sources(topdir, added=[], removed=[]):
    path = sources_path(topdir)
    entries = {}
    if os.path.isfile(path):
        entries = parse_sources(path)
    f = open(path, "w") # open before calculating hashes
    for name in removed:
	if name in entries:
           del entries[name]
    for added_path in added:
        name = os.path.basename(added_path)
        entries[name] = file_hash(added_path)
    for name in sorted(entries):
        f.write("%s  %s\n" % (entries[name], name))
    f.close()

def update_sources_threaded(*args, **kwargs):
    t = threading.Thread(target=update_sources, args=args, kwargs=kwargs)
    t.start()
    t.join()
    return t

def remove(path, message=None, commit=True):
    from MgaRepo.rpmutil import getpkgtopdir
    svn = SVN()
    if not os.path.exists(path):
        raise Error, "not found: %s" % path
    bpath = os.path.basename(path)
    topdir = getpkgtopdir()
    bintopdir = translate_topdir(topdir)
    sources = sources_path(topdir)
    svn.update(sources)
    update = update_sources_threaded(topdir, removed=[bpath])
    silent = config.get("log", "ignore-string", "SILENT")
    if not message:
        message = "%s: delete binary file %s" % (silent, bpath)
    if commit:
        svn.commit(topdir + " " + sources, log=message, nonrecursive=True)
    binlink = os.path.join(topdir, "SOURCES", bpath)
    if os.path.islink(binlink):
        os.unlink(binlink)
    binpath = os.path.join(topdir, BINARIES_CHECKOUT_NAME, bpath)
    svn.remove(binpath)
    if commit:
       svn.commit(binpath, log=message)

def upload(path, message=None):
    from MgaRepo.rpmutil import getpkgtopdir
    svn = SVN()
    if not os.path.exists(path):
        raise Error, "not found: %s" % path
    # XXX check if the path is under SOURCES/
    paths = find_binaries([path])
    if not paths:
        raise Error, "'%s' does not seem to have any tarballs" % path
    topdir = getpkgtopdir()
    bintopdir = translate_topdir(topdir)
    binurl = mirror._joinurl(bintopdir, BINARIES_DIR_NAME)
    sourcesdir = os.path.join(topdir, "SOURCES")
    bindir = os.path.join(topdir, BINARIES_CHECKOUT_NAME)
    silent = config.get("log", "ignore-string", "SILENT")
    if not os.path.exists(bindir):
        try:
            download(topdir, show=False)
        except Error:
            # possibly the package does not exist
            # (TODO check whether it is really a 'path not found' error)
            pass
        if not os.path.exists(bindir):
            create_package_dirs(bintopdir)
            svn.commit(topdir, log="%s: created binrepo structure" % silent)
            download(topdir, show=False)
    for path in paths:
        if svn.info2(path):
            sys.stderr.write("'%s' is already tracked by svn, ignoring\n" %
                    path)
            continue
	if os.path.islink(path):
            sys.stderr.write("'%s' is a symbolic link, ignoring\n" %
                    path)
            continue
        name = os.path.basename(path)
        binpath = os.path.join(bindir, name)
        os.rename(path, binpath)
        svn.add(binpath)
    if not message:
        message = "%s: new binary files %s" % (silent, " ".join(paths))
    make_symlinks(bindir, sourcesdir)
    sources = sources_path(topdir)
    if svn.info2(sources):
	svn.update(sources)
    update = update_sources_threaded(topdir, added=paths)
    rev = svn.commit(binpath, log=message)
    svn.propset(PROP_BINREPO_REV, str(rev), topdir)
    if svn.info2(sources):
	svn.update(sources)
    else:
	svn.add(sources)
    update.join()
    svn.commit(topdir + " " + sources, log=message, nonrecursive=True)

def mapped_revision(target, revision, wc=False):
    """Maps a txtrepo revision to a binrepo datespec

    This datespec can is intended to be used by svn .. -r DATE.

    @target: a working copy path or a URL
    @revision: if target is a URL, the revision number used when fetching
         svn info
    @wc: if True indicates that 'target' must be interpreted as a
         the path of a svn working copy, otherwise it is handled as a URL
    """
    svn = SVN()
    binrev = None
    if wc:
        spath = sources_path(target)
        if os.path.exists(spath):
            infolines = svn.info(spath, xml=True)
            if infolines:
                rawinfo = "".join(infolines) # arg!
                found = re.search("<date>(.*?)</date>", rawinfo).groups()
                date = found[0]
            else:
                raise Error, "bogus 'svn info' for '%s'" % spath
        else:
            raise Error, "'%s' was not found" % spath
    else:
        url = mirror._joinurl(target, sources_path(""))
        date = svn.propget("svn:date", url, rev=revision, revprop=True)
        if not date:
            raise Error, "no valid date available for '%s'" % url
    binrev = "{%s}" % date
    return binrev

def markrelease(sourceurl, releasesurl, version, release, revision):
    svn = SVN()
    binrev = mapped_revision(sourceurl, revision)
    binsource = translate_url(sourceurl)
    binreleases = translate_url(releasesurl)
    versiondir = mirror._joinurl(binreleases, version)
    dest = mirror._joinurl(versiondir, release)
    svn.mkdir(binreleases, noerror=1, log="created directory for releases")
    svn.mkdir(versiondir, noerror=1, log="created directory for version %s" % version)
    svn.copy(binsource, dest, rev=binrev,
            log="%%markrelease ver=%s rel=%s rev=%s binrev=%s" % (version, release,
                revision, binrev))
