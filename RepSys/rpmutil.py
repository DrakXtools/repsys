#!/usr/bin/python
from RepSys import Error, config, RepSysTree
from RepSys import mirror
from RepSys.svn import SVN
from RepSys.simplerpm import SRPM
from RepSys.log import specfile_svn2rpm
from RepSys.util import execcmd
from RepSys.command import default_parent
import rpm
import tempfile
import shutil
import glob
import sys
import os

def get_spec(pkgdirurl, targetdir=".", submit=False):
    svn = SVN(baseurl=pkgdirurl)
    tmpdir = tempfile.mktemp()
    try:
        geturl = "/".join([pkgdirurl, "current", "SPECS"])
        svn.export("'%s'" % geturl, tmpdir)
        speclist = glob.glob(os.path.join(tmpdir, "*.spec"))
        if not speclist:
            raise Error, "no spec files found"
        spec = speclist[0]
        shutil.copy(spec, targetdir)
    finally:
        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)

def rpm_macros_defs(macros):
    defs = ("--define \"%s %s\"" % macro for macro in macros)
    args = " ".join(defs)
    return args

def get_srpm(pkgdirurl,
             mode = "current",
             targetdirs = None,
             version = None,
             release = None,
             revision = None,
             packager = "",
             revname = 0,
             svnlog = 0,
             scripts = [], 
             submit = False,
             template = None,
             macros = [],
             verbose = 0):
    svn = SVN(baseurl=pkgdirurl)
    tmpdir = tempfile.mktemp()
    topdir = "--define '_topdir %s'" % tmpdir
    builddir = "--define '_builddir %s/%s'" % (tmpdir, "BUILD")
    rpmdir = "--define '_rpmdir %s/%s'" % (tmpdir, "RPMS")
    sourcedir = "--define '_sourcedir %s/%s'" % (tmpdir, "SOURCES")
    specdir = "--define '_specdir %s/%s'" % (tmpdir, "SPECS")
    srcrpmdir = "--define '_srcrpmdir %s/%s'" % (tmpdir, "SRPMS")
    patchdir = "--define '_patchdir %s/%s'" % (tmpdir, "SOURCES")
    try:
        if mode == "version":
            geturl = os.path.join(pkgdirurl, "versions",
                                  version, release)
        elif mode == "pristine":
            geturl = os.path.join(pkgdirurl, "pristine")
        elif mode == "current" or mode == "revision":
            geturl = os.path.join(pkgdirurl, "current")
        else:
            raise Error, "unsupported get_srpm mode: %s" % mode
        svn.export(geturl, tmpdir, rev=revision)
        srpmsdir = os.path.join(tmpdir, "SRPMS")
        os.mkdir(srpmsdir)
        specsdir = os.path.join(tmpdir, "SPECS")
        speclist = glob.glob(os.path.join(specsdir, "*.spec"))
        if not speclist:
            raise Error, "no spec files found"
        spec = speclist[0]
        if svnlog:
            submit = not not revision
            specfile_svn2rpm(pkgdirurl, spec, revision, submit=submit,
                    template=template, macros=macros, exported=tmpdir)
        #FIXME revisioreal not needed if revision is None
        #FIXME use geturl instead of pkgdirurl
        revisionreal = svn.revision(pkgdirurl)
        for script in scripts:
            #FIXME revision can be "None"
            status, output = execcmd(script, tmpdir, spec, str(revision),
                                     noerror=1)
            if status != 0:
                raise Error, "script %s failed" % script
        if packager:
            packager = " --define 'packager %s'" % packager

        defs = rpm_macros_defs(macros)
        execcmd("rpm -bs --nodeps %s %s %s %s %s %s %s %s %s %s" %
            (topdir, builddir, rpmdir, sourcedir, specdir, 
             srcrpmdir, patchdir, packager, spec, defs))

        if revision and revisionreal:
            #FIXME duplicate glob line
            srpm = glob.glob(os.path.join(srpmsdir, "*.src.rpm"))[0]
            srpminfo = SRPM(srpm)
            release = srpminfo.release
            srpmbase = os.path.basename(srpm)
            os.rename(srpm, "%s/@%s:%s" % (srpmsdir, revisionreal, srpmbase))
        srpm = glob.glob(os.path.join(srpmsdir, "*.src.rpm"))[0]
        if not targetdirs:
            targetdirs = (".",)
        targetsrpms = []
        for targetdir in targetdirs:
            targetsrpm = os.path.join(os.path.realpath(targetdir), 
                    os.path.basename(srpm))
            targetsrpms.append(targetsrpm)
            if verbose:
                sys.stderr.write("Wrote: %s\n" %  targetsrpm)
            execcmd("cp -f", srpm, targetdir)
        os.unlink(srpm)
        return targetsrpms
    finally:
        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)

def patch_spec(pkgdirurl, patchfile, log=""):
    svn = SVN(baseurl=pkgdirurl)
    tmpdir = tempfile.mktemp()
    try:
        geturl = "/".join([pkgdirurl, "current", "SPECS"])
        svn.checkout(geturl, tmpdir)
        speclist = glob.glob(os.path.join(tmpdir, "*.spec"))
        if not speclist:
            raise Error, "no spec files found"
        spec = speclist[0]
        status, output = execcmd("patch", spec, patchfile)
        if status != 0:
            raise Error, "can't apply patch:\n%s\n" % output
        else:
            svn.commit(tmpdir, log="")
    finally:
        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)

def put_srpm(pkgdirurl, srpmfile, appendname=0, log=""):
    srpm = SRPM(srpmfile)
    if appendname:
        pkgdirurl = "/".join([pkgdirurl, srpm.name])
    svn = SVN(baseurl=pkgdirurl)
    tmpdir = tempfile.mktemp()
    try:
        if srpm.epoch:
            version = "%s:%s" % (srpm.epoch, srpm.version)
        else:
            version = srpm.version
        versionurl = "/".join([pkgdirurl, "releases", version])
        releaseurl = "/".join([versionurl, srpm.release])
        #FIXME when pre-commit hook fails, there's no clear way to know
        # what happened
        ret = svn.mkdir(pkgdirurl, noerror=1, log="Created package directory")
        if ret:
            svn.checkout(pkgdirurl, tmpdir)
            svn.mkdir(os.path.join(tmpdir, "releases"))
            svn.mkdir(os.path.join(tmpdir, "releases", version))
            svn.mkdir(os.path.join(tmpdir, "current"))
            svn.mkdir(os.path.join(tmpdir, "current", "SPECS"))
            svn.mkdir(os.path.join(tmpdir, "current", "SOURCES"))
            #svn.commit(tmpdir,log="Created package structure.")
            version_exists = 1
            currentdir = os.path.join(tmpdir, "current")
        else:
            if svn.ls(releaseurl, noerror=1):
                raise Error, "release already exists"
            svn.checkout("/".join([pkgdirurl, "current"]), tmpdir)
            svn.mkdir(versionurl, noerror=1,
                      log="Created directory for version %s." % version)
            currentdir = tmpdir
         
        specsdir = os.path.join(currentdir, "SPECS")
        sourcesdir = os.path.join(currentdir, "SOURCES")

        unpackdir = tempfile.mktemp()
        os.mkdir(unpackdir)
        try:
            srpm.unpack(unpackdir)

            uspecsdir = os.path.join(unpackdir, "SPECS")
            usourcesdir = os.path.join(unpackdir, "SOURCES")
            
            uspecsentries = os.listdir(uspecsdir)
            usourcesentries = os.listdir(usourcesdir)
            specsentries = os.listdir(specsdir)
            sourcesentries = os.listdir(sourcesdir)

            # Remove old entries
            for entry in [x for x in specsentries
                             if x not in uspecsentries]:
                if entry == ".svn":
                    continue
                entrypath = os.path.join(specsdir, entry)
                os.unlink(entrypath)
                svn.remove(entrypath)
            for entry in [x for x in sourcesentries
                             if x not in usourcesentries]:
                if entry == ".svn":
                    continue
                entrypath = os.path.join(sourcesdir, entry)
                os.unlink(entrypath)
                svn.remove(entrypath)

            # Copy all files
            execcmd("cp -rf", uspecsdir, currentdir)
            execcmd("cp -rf", usourcesdir, currentdir)
            
            # Add new entries
            for entry in [x for x in uspecsentries
                             if x not in specsentries]:
                entrypath = os.path.join(specsdir, entry)
                svn.add(entrypath)
            for entry in [x for x in usourcesentries
                             if x not in sourcesentries]:
                entrypath = os.path.join(sourcesdir, entry)
                svn.add(entrypath)
        finally:
            if os.path.isdir(unpackdir):
                shutil.rmtree(unpackdir)

        svn.commit(tmpdir, log=log)
    finally:
        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)

    # Do revision and pristine tag copies
    pristineurl = os.path.join(pkgdirurl, "pristine")
    svn.remove(pristineurl, noerror=1,
               log="Removing previous pristine/ directory.")
    currenturl = os.path.join(pkgdirurl, "current")
    svn.copy(currenturl, pristineurl,
             log="Copying release %s-%s to pristine/ directory." %
                 (version, srpm.release))
    svn.copy(currenturl, releaseurl,
             log="Copying release %s-%s to releases/ directory." %
                 (version, srpm.release))

def create_package(pkgdirurl, log="", verbose=0):
    svn = SVN(baseurl=pkgdirurl)
    tmpdir = tempfile.mktemp()
    try:
        basename = RepSysTree.pkgname(pkgdirurl)
        if verbose:
            print "Creating package directory...",
        sys.stdout.flush()
        ret = svn.mkdir(pkgdirurl,
                        log="Created package directory for '%s'." % basename)
        if verbose:
            print "done"
            print "Checking it out...",
        svn.checkout(pkgdirurl, tmpdir)
        if verbose:
            print "done"
            print "Creating package structure...",
        svn.mkdir(os.path.join(tmpdir, "current"))
        svn.mkdir(os.path.join(tmpdir, "current", "SPECS"))
        svn.mkdir(os.path.join(tmpdir, "current", "SOURCES"))
        if verbose:
            print "done"
            print "Committing...",
        svn.commit(tmpdir,
                   log="Created package structure for '%s'." % basename)
        print "done"
    finally:
        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)


def create_markrelease_log(version, release, revision):
    log = """%%repsys markrelease
version: %s
release: %s
revision: %s

%s""" % (version, release, revision, 
        ("Copying %s-%s to releases/ directory." % (version, release)))
    return log

def mark_release(pkgdirurl, version, release, revision):
    svn = SVN(baseurl=pkgdirurl)
    releasesurl = "/".join([pkgdirurl, "releases"])
    versionurl = "/".join([releasesurl, version])
    releaseurl = "/".join([versionurl, release])
    if svn.ls(releaseurl, noerror=1):
        raise Error, "release already exists"
    svn.mkdir(releasesurl, noerror=1,
              log="Created releases directory.")
    svn.mkdir(versionurl, noerror=1,
              log="Created directory for version %s." % version)
    pristineurl = os.path.join(pkgdirurl, "pristine")
    svn.remove(pristineurl, noerror=1,
               log="Removing previous pristine/ directory.")
    currenturl = os.path.join(pkgdirurl, "current")
    svn.copy(currenturl, pristineurl,
             log="Copying release %s-%s to pristine/ directory." %
                 (version, release))
    markreleaselog = create_markrelease_log(version, release, revision)
    svn.copy(currenturl, releaseurl, rev=revision,
             log=markreleaselog)

def check_changed(pkgdirurl, all=0, show=0, verbose=0):
    svn = SVN(baseurl=pkgdirurl)
    if all:
        baseurl = pkgdirurl
        packages = []
        if verbose:
            print "Getting list of packages...",
            sys.stdout.flush()
        packages = [x[:-1] for x in svn.ls(baseurl)]
        if verbose:
            print "done"
        if not packages:
            raise Error, "couldn't get list of packages"
    else:
        baseurl, basename = os.path.split(pkgdirurl)
        packages = [basename]
    clean = []
    changed = []
    nopristine = []
    nocurrent = []
    for package in packages:
        pkgdirurl = os.path.join(baseurl, package)
        current = os.path.join(pkgdirurl, "current")
        pristine = os.path.join(pkgdirurl, "pristine")
        if verbose:
            print "Checking package %s..." % package,
            sys.stdout.flush()
        if not svn.ls(current, noerror=1):
            if verbose:
                print "NO CURRENT"
            nocurrent.append(package)
        elif not svn.ls(pristine, noerror=1):
            if verbose:
                print "NO PRISTINE"
            nopristine.append(package)
        else:
            diff = svn.diff(pristine, current)
            if diff:
                changed.append(package)
                if verbose:
                    print "CHANGED"
                if show:
                    print diff
            else:
                if verbose:
                    print "clean"
                clean.append(package)
    if verbose:
        if not packages:
            print "No packages found!"
        elif all:
            print "Total clean packages: %s" % len(clean)
            print "Total CHANGED packages: %d" % len(changed)
            print "Total NO CURRENT packages: %s" % len(nocurrent)
            print "Total NO PRISTINE packages: %s" % len(nopristine)
    return {"clean": clean,
            "changed": changed,
            "nocurrent": nocurrent,
            "nopristine": nopristine}

def checkout(pkgdirurl, path=None, revision=None):
    o_pkgdirurl = pkgdirurl
    pkgdirurl = default_parent(o_pkgdirurl)
    current = os.path.join(pkgdirurl, "current")
    if path is None:
        _, path = os.path.split(pkgdirurl)
    # if default_parent changed the URL, we can use mirrors because the
    # user did not provided complete package URL
    if (o_pkgdirurl != pkgdirurl) and mirror.enabled():
        current = mirror.checkout_url(current)
        print "checking out from mirror", current
    svn = SVN(baseurl=pkgdirurl)
    svn.checkout(current, path, rev=revision, show=1)

def _getpkgtopdir(basedir=None):
    if basedir is None:
        basedir = os.getcwd()
    cwd = os.getcwd()
    dirname = os.path.basename(cwd)
    if dirname == "SPECS" or dirname == "SOURCES":
        topdir = os.pardir
    else:
        topdir = ""
    return topdir

def sync(dryrun=False):
    svn = SVN(noauth=True)
    topdir = _getpkgtopdir()
    # run svn info because svn st does not complain when topdir is not an
    # working copy
    svn.info(topdir or ".")
    specsdir = os.path.join(topdir, "SPECS/")
    sourcesdir = os.path.join(topdir, "SOURCES/")
    for path in (specsdir, sourcesdir):
        if not os.path.isdir(path):
            raise Error, "%s directory not found" % path
    specs = glob.glob(os.path.join(specsdir, "*.spec"))
    if not specs:
        raise Error, "no .spec files found in %s" % specsdir
    specpath = specs[0] # FIXME better way?
    try:
        rpm.addMacro("_topdir", os.path.abspath(topdir))
        spec = rpm.TransactionSet().parseSpec(specpath)
    except rpm.error, e:
        raise Error, "could not load spec file: %s" % e
    sources = [os.path.basename(name)
            for name, no, flags in spec.sources()]
    sourcesst = dict((os.path.basename(path), st)
            for st, path in svn.status(sourcesdir, noignore=True))
    toadd = []
    for source in sources:
        sourcepath = os.path.join(sourcesdir, source)
        if sourcesst.get(source):
            if os.path.isfile(sourcepath):
                toadd.append(sourcepath)
            else:
                sys.stderr.write("warning: %s not found\n" % sourcepath)
    # rm entries not found in sources and still in svn
    found = os.listdir(sourcesdir)
    toremove = []
    for entry in found:
        if entry == ".svn":
            continue
        status = sourcesst.get(entry)
        if status is None and entry not in sources:
            path = os.path.join(sourcesdir, entry)
            toremove.append(path)
    for path in toremove:
        print "D\t%s" % path
        if not dryrun:
            svn.remove(path, local=True)
    for path in toadd:
        print "A\t%s" % path
        if not dryrun:
            svn.add(path, local=True)

def commit(target=".", message=None):
    svn = SVN(noauth=True)
    status = svn.status(target, quiet=True)
    if not status:
        print "nothing to commit"
        return
    info = svn.info2(target)
    url = info.get("URL")
    if url is None:
        raise Error, "working copy URL not provided by svn info"
    mirrored = mirror.enabled(url)
    if mirrored:
        newurl = mirror.switchto_parent(svn, url, target)
        print "relocated to", newurl
    # we can't use the svn object here because pexpect hides VISUAL
    mopt = ""
    if message is not None:
        mopt = "-m \"%s\"" % message
    os.system("svn ci %s %s" % (mopt, target))
    if mirrored:
        print "use \"repsys switch\" in order to switch back to mirror "\
                "later"

def switch(mirrorurl=None):
    svn  = SVN(noauth=True)
    topdir = _getpkgtopdir()
    info = svn.info2(topdir)
    wcurl = info.get("URL")
    if wcurl is None:
        raise Error, "working copy URL not provided by svn info"
    newurl = mirror.autoswitch(svn, topdir, wcurl, mirrorurl)
    print "switched to", newurl

def get_submit_info(path):
    path = os.path.abspath(path)

    # First, look for SPECS and SOURCES directories.
    found = False
    while path != "/":
        if os.path.isdir(path):
            specsdir = os.path.join(path, "SPECS")
            sourcesdir = os.path.join(path, "SOURCES")
            if os.path.isdir(specsdir) and os.path.isdir(sourcesdir):
                found = True
                break
        path = os.path.dirname(path)
    if not found:
        raise Error, "SPECS and/or SOURCES directories not found"

    # Then, check if this is really a subversion directory.
    if not os.path.isdir(os.path.join(path, ".svn")):
        raise Error, "subversion directory not found"
    
    svn = SVN(baseurl=pkgdirurl)


    # Now, extract the package name.
    for line in svn.info(path):
        if line.startswith("URL: "):
            url = line.split()[1]
            toks = url.split("/")
            if len(toks) < 2 or toks[-1] != "current":
                raise Error, "unexpected URL received from 'svn info'"
            name = toks[-2]
            break
    else:
        raise Error, "URL tag not found in 'svn info' output"

    # Finally, guess revision.
    max = -1
    files = []
    files.extend(glob.glob("%s/*" % specsdir))
    files.extend(glob.glob("%s/*" % sourcesdir))
    for line in svn.info(" ".join(files)):
        if line.startswith("Revision: "):
            rev = int(line.split()[1])
            if rev > max:
                max = rev
    if max == -1:
        raise Error, "revision tag not found in 'svn info' output"
    
    return name, max

# vim:et:ts=4:sw=4
