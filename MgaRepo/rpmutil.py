from MgaRepo import Error, config
from MgaRepo import mirror, layout, log, binrepo
from MgaRepo.simplerpm import SRPM
from MgaRepo.util import execcmd, CommandError
from MgaRepo.git import GIT
from MgaRepo.svn import SVN
from MgaRepo.vcsutil import detectVCS
from MgaRepo.command import default_parent
import rpm
import urllib.parse
import tempfile
import shutil
import string
import glob
import sys
import os

def get_spec(pkgdirurl, targetdir=".", submit=False):
    svn = detectVCS(pkgdirurl)
    tmpdir = tempfile.mktemp()
    try:
        geturl = layout.checkout_url(pkgdirurl, append_path="SPECS")
        mirror.info(geturl)
        svn.export(geturl, tmpdir)
        speclist = glob.glob(os.path.join(tmpdir, "*.spec"))
        if not speclist:
            raise Error("no spec files found")
        spec = speclist[0]
        shutil.copy(spec, targetdir)
        name = os.path.basename(spec)
        path = os.path.join(targetdir, name)
        print("Wrote %s" % (name))
    finally:
        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)

#FIXME move it to another module
def rev_touched_url(url, rev):
    svn = detectVCS(url)
    info = svn.info2(url)
    if info is None:
        raise Error("can't fetch svn info about the URL: %s" % url)
    root = info["Repository Root"]
    urlpath = url[len(root):]
    touched = False
    entries = svn.log(root, start=rev, limit=1)
    entry = entries[0]
    for change in entry.changed:
        path = change.get("path")
        if path and path.startswith(urlpath):
            touched = True
    return touched

def cp_srpms(revision, revname, geturl, targetdirs, srpmsdir, verbose):
    targetsrpms = []
    urlrev = None
    if revname:
        urlrev = revision or layout.get_url_revision(geturl)
    if not targetdirs:
        targetdirs = (".",)
    srpms = glob.glob(os.path.join(srpmsdir, "*.src.rpm"))
    if not srpms:
        # something fishy happened
        raise Error("no SRPMS were found at %s" % srpmsdir)
    for srpm in srpms:
        name = os.path.basename(srpm)
        if revname:
            name = "@%s:%s" % (urlrev, name)
        for targetdir in targetdirs:
            newpath = os.path.join(targetdir, name)
            targetsrpms.append(newpath)
            if os.path.exists(newpath):
                # should we warn?
                os.unlink(newpath)
            shutil.copy(srpm, newpath)
            if verbose:
                sys.stderr.write("Wrote: %s\n" %  newpath)
    return targetsrpms

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
             verbose = 0,
             strict = False,
             fullnames = False):
    svn = detectVCS(pkgdirurl)
    tmpdir = tempfile.mktemp()
    topdir = "_topdir %s" % tmpdir
    builddir = "_builddir %s/%s" % (tmpdir, "BUILD")
    rpmdir = "_rpmdir %s/%s" % (tmpdir, "RPMS")
    sourcedir = "_sourcedir %s/%s" % (tmpdir, "SOURCES")
    specdir = "_specdir %s/%s" % (tmpdir, "SPECS")
    srcrpmdir = "_srcrpmdir %s/%s" % (tmpdir, "SRPMS")
    patchdir = "_patchdir %s/%s" % (tmpdir, "SOURCES")
    temppath = "_tmppath %s" % (tmpdir)

    rpmdefs = [("--define", expr) for expr in (topdir, builddir, rpmdir,
        sourcedir, specdir, srcrpmdir, patchdir, temppath)]

    try:
        if mode == "version":
            geturl = layout.checkout_url(pkgdirurl, version=version,
                    release=release)
        elif mode == "pristine":
            geturl = layout.checkout_url(pkgdirurl, pristine=True)
        elif mode == "current" or mode == "revision":
            #FIXME we should handle revisions specified using @REV
            geturl = layout.checkout_url(pkgdirurl)
        else:
            raise Error("unsupported get_srpm mode: %s" % mode)
        strict = strict or config.getbool("submit", "strict-revision", False)
        if strict and not rev_touched_url(geturl, revision):
            #FIXME would be nice to have the revision number even when
            # revision is None
            raise Error("the revision %s does not change anything "\
                    "inside %s" % (revision or "HEAD", geturl))
        mirror.info(geturl)
        svn.export(geturl, tmpdir, rev=revision)
        binrepo.download_binaries(tmpdir)
        srpmsdir = os.path.join(tmpdir, "SRPMS")
        os.mkdir(srpmsdir)
        specsdir = os.path.join(tmpdir, "SPECS")
        speclist = glob.glob(os.path.join(specsdir, "*.spec"))
        if config.getbool("srpm", "run-prep", False):
            makefile = os.path.join(tmpdir, "Makefile")
            if os.path.exists(makefile):
                execcmd(("make", "-C", tmpdir, "srpm-prep"))
        if not speclist:
            raise Error("no spec files found")
        spec = speclist[0]

        sourcecmd = config.get("helper", "rpmbuild", "rpmbuild")
        if packager:
            packager = " --define 'packager %s'" % packager
        sourcecmd = config.get("helper", "rpmbuild", "rpmbuild")
        args = [sourcecmd, "-bs", "--nodeps"]
        for pair in rpmdefs:
            args.extend(pair)
        for pair in macros:
            args.extend(("--define", "%s %s" % pair))
        args.append(spec)
        if svnlog:
            submit = not not revision
            try:
                log.specfile_svn2rpm(pkgdirurl, spec, revision, submit=submit,
                    template=template, macros=macros, exported=tmpdir, fullnames=fullnames)
            except:
                #cmd = [sourcecmd, topdir, builddir, rpmdir, sourcedir, specdir
                execcmd(args)
                cp_srpms(revision, revname, geturl, targetdirs, srpmsdir, verbose)
                log.specfile_svn2rpm(pkgdirurl, spec, revision, submit=submit,
                    template=template, macros=macros, exported=tmpdir, create=True)
            
        for script in scripts:
            #FIXME revision can be "None"
            status, output = execcmd(script, tmpdir, spec, str(revision),
                                     noerror=1)
            if status != 0:
                raise Error("script %s failed" % script)

        try:
            execcmd(args)
        except CommandError as e:
            if config.getbool("global", "verbose"):
                cmdline = e.cmdline + "\n"
            else:
                cmdline = ""
            raise Error("error while creating the source RPM "
                        "(with %s):\n%s%s" % (sourcecmd, cmdline, e.output))

        # copy the generated SRPMs to their target locations
        targetsrpms = cp_srpms(revision, revname, geturl, targetdirs, srpmsdir, verbose)
        return targetsrpms
    finally:
        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)

def patch_spec(pkgdirurl, patchfile, log=""):
    #FIXME use get_spec
    svn = detectVCS(pkgdirurl)
    tmpdir = tempfile.mktemp()
    try:
        geturl = layout.checkout_url(pkgdirurl, append_path="SPECS")
        svn.checkout(geturl, tmpdir)
        speclist = glob.glob(os.path.join(tmpdir, "*.spec"))
        if not speclist:
            raise Error("no spec files found")
        spec = speclist[0]
        status, output = execcmd(["patch", spec, patchfile])
        if status != 0:
            raise Error("can't apply patch:\n%s\n" % output)
        else:
            svn.commit(tmpdir, log="")
    finally:
        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)

def put_srpm(srpmfile, markrelease=False, striplog=True, branch=None,
        baseurl=None, baseold=None, logmsg=None, rename=True):
    srpm = SRPM(srpmfile)
    tmpdir = tempfile.mktemp()
    if baseurl:
        pkgurl = mirror._joinurl(baseurl, srpm.name)
    else:
        pkgurl = layout.package_url(srpm.name, distro=branch,
                mirrored=False)
    svn = detectVCS(pkgurl)
    print("Importing package to %s" % pkgurl)
    try:
        if srpm.epoch:
            version = "%s:%s" % (srpm.epoch, srpm.version)
        else:
            version = srpm.version
        versionurl = "/".join([pkgurl, "releases", version])
        releaseurl = "/".join([versionurl, srpm.release])
        currenturl = "/".join([pkgurl, "current"])
        currentdir = os.path.join(tmpdir, "current")
        ret = svn.mkdir(pkgurl, noerror=1, log="Created package directory")
        if ret or not svn.ls(currenturl, noerror=1):
            svn.checkout(pkgurl, tmpdir)
            svn.mkdir(os.path.join(tmpdir, "releases"))
            svn.mkdir(currentdir)
            svn.mkdir(os.path.join(currentdir, "SPECS"))
            svn.mkdir(os.path.join(currentdir, "SOURCES"))
            #svn.commit(tmpdir,log="Created package structure.")
            version_exists = 1
        else:
            raise Error("package already exists or error creating package directory")
         
        specsdir = os.path.join(currentdir, "SPECS")
        sourcesdir = os.path.join(currentdir, "SOURCES")

        unpackdir = tempfile.mktemp()
        os.mkdir(unpackdir)
        try:
            srpm.unpack(unpackdir)

            uspecsdir = os.path.join(unpackdir, "SPECS")
            usourcesdir = os.path.join(unpackdir, "SOURCES")
            
            uspecsentries = os.listdir(uspecsdir)
            if os.path.isdir(usourcesdir):
                usourcesentries = os.listdir(usourcesdir)
            else:
                usourcesentries=[]
            specsentries = os.listdir(specsdir)
            if os.path.isdir(sourcesdir):
                sourcesentries = os.listdir(sourcesdir)
            else:
                sourcesentries=[]

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
            execcmd(["cp", "-rf", uspecsdir, currentdir])
            if os.path.isdir(usourcesdir):
                execcmd(["cp", "-rlf", usourcesdir, currentdir])
            
            # Add new entries
            for entry in [x for x in uspecsentries
                             if x not in specsentries]:
                entrypath = os.path.join(specsdir, entry)
                svn.add(entrypath)
            for entry in [x for x in usourcesentries
                             if x not in sourcesentries]:
                entrypath = os.path.join(sourcesdir, entry)
                if binrepo.is_binary(entrypath):
                    continue
                svn.add(entrypath)
        finally:
            if os.path.isdir(unpackdir):
                shutil.rmtree(unpackdir)

        specs = glob.glob(os.path.join(specsdir, "*.spec"))
        if not specs:
            raise Error("no spec file found on %s" % specsdir)
        if len(specs) > 1:
            raise Error("more than one spec file found on %s" % specsdir)
        specpath = specs[0]
        if rename:
            specfile = os.path.basename(specpath)
            specname = specfile[:-len(".spec")]
            if specname != srpm.name:
                newname = srpm.name + ".spec"
                newpath = os.path.join(specsdir, newname)
                sys.stderr.write("warning: renaming spec file to '%s' "
                        "(use -n to disable it)\n" % (newname))
                os.rename(specpath, newpath)
                try:
                    svn.remove(specpath)
                except Error:
                    # file not tracked
                    svn.revert(specpath)
                svn.add(newpath)
                specpath = newpath

        if striplog:
            specpath = specpath
            with open(specpath, "r", encoding='utf-8') as fspec:
                spec, chlog = log.split_spec_changelog(fspec)
            with open(specpath, "w", encoding='utf-8') as fspec:
                fspec.writelines(spec)
            chlog.seek(0, os.SEEK_END)
            if chlog.tell() != 0:
                chlog.seek(0)
                #FIXME move it to layout.py
                oldurl = baseold or config.get("log", "oldurl")
                if oldurl == '.' or oldurl.startswith('./'):
                    pkgoldurl = os.path.join(pkgurl, oldurl)
                else:
                    pkgoldurl = mirror._joinurl(oldurl, srpm.name)
                svn.mkdir(pkgoldurl, noerror=1,
                        log="created old log directory for %s" % srpm.name)
                logtmp = tempfile.mktemp()
                try:
                    svn.checkout(pkgoldurl, logtmp)
                    miscpath = os.path.join(logtmp, "log")
                    with open(miscpath, "w+", encoding='utf-8') as fmisc:
                        fmisc.writelines(chlog)
                    svn.add(miscpath)
                    svn.commit(logtmp,
                            log="imported old log for %s" % srpm.name)
                finally:
                    if os.path.isdir(logtmp):
                        shutil.rmtree(logtmp)
        binrepo.import_binaries(currentdir, srpm.name)
        svn.commit(tmpdir,
                log=logmsg or ("imported package %s" % srpm.name))
    finally:
        if os.path.isdir(tmpdir):
            shutil.rmtree(tmpdir)

    # Do revision and pristine tag copies
    pristineurl = layout.checkout_url(pkgurl, pristine=True)
    svn.remove(pristineurl, noerror=1,
               log="Removing previous pristine/ directory.")
    currenturl = layout.checkout_url(pkgurl)
    svn.copy(currenturl, pristineurl,
             log="Copying release %s-%s to pristine/ directory." %
                 (version, srpm.release))
    if markrelease:
        svn.copy(currenturl, releaseurl,
                 log="Copying release %s-%s to releases/ directory." %
                     (version, srpm.release))

def build_rpm(build_cmd="b",
        verbose=True,
        rpmlint=True,
        short_circuit=False,
        packager = None,
        installdeps = True,
        use_dnf = False,
        svnlog = False,
        fullnames = True,
        macros = [],
        **rpmargs):
    top = os.getcwd()
    topdir = "_topdir %s" % top
    builddir = "_builddir %s/%s" % (top, "BUILD")
    rpmdir = "_rpmdir %s/%s" % (top, "RPMS")
    sourcedir = "_sourcedir %s/%s" % (top, "SOURCES")
    specdir = "_specdir %s/%s" % (top, "SPECS")
    srcrpmdir = "_srcrpmdir %s/%s" % (top, "SRPMS")
    patchdir = "_patchdir %s/%s" % (top, "SOURCES")

    build = os.path.join(top, "BUILD")
    if not os.path.exists(build):
        os.mkdir(build)
    specsdir = os.path.join(top, "SPECS")
    speclist = glob.glob(os.path.join(specsdir, "*.spec"))
    if not speclist:
        raise Error("no spec files found")
    spec = speclist[0]

    # If we're building package with %changelog, we'll make a temporary
    # copy of the spec file with %changelog applied that we'll use for
    # building. This way we avoid modifying files in repository.
    # TODO: implement support for external changelog in rpm
    if svnlog:
        vcs = detectVCS(top)
        specsdir = tempfile.mkdtemp()
        shutil.copy(spec, specsdir)
        specdir = "_specdir "+specsdir
        spec = os.path.join(specsdir,os.path.basename(spec))
        info = vcs.info2(top)
        pkgdirurl = layout.remove_current(info["URL"])
        log.specfile_svn2rpm(pkgdirurl, spec, rev=None, submit=False,
                    template=None, macros=macros, exported=top, fullnames=fullnames)

    rpmdefs = [("--define", expr) for expr in (topdir, builddir, rpmdir,
        sourcedir, specdir, srcrpmdir, patchdir)]

    if packager:
        rpmdefs.append(("--define", "packager %s" % packager))

    if rpmlint:
        rpmdefs.append(("--define", "_build_pkgcheck_set %{_bindir}/rpmlint"))

    rpmbuild = config.get("helper", "rpmbuild", "rpmbuild")
    args = [rpmbuild, spec]
    if short_circuit:
        args.append("--short-circuit")
    for pair in rpmdefs:
        args.extend(pair)
    for pair in macros:
        args.extend(("--define", "%s %s" % pair))
    args.extend(("--define", "_disable_source_fetch 0"))
    args.extend(*rpmargs.values())
    os.environ["LC_ALL"] = "C"
    # First check whether dependencies are satisfied
    status, output = execcmd(*args + ["--nobuild"], show=verbose, collecterr=True, noerror=True)
    if status:
        if "error: Failed build dependencies:" in output:
            if not installdeps:
                raise Error("Automatic installation of dependencies disabled,"
                "aborting...")
            else:
                if verbose:
                    print("Installing missing build dependencies")
                if use_dnf:
                    pkg_mgr_base = ["dnf"]
                    pkg_mgr_builddep = pkg_mgr_base + ["--assume-yes", "--setopt=install_weak_deps=False", "builddep"]
                else:
                    pkg_mgr_base = ["urpmi"]
                    pkg_mgr_builddep = pkg_mgr_base + ["--auto", "--buildrequires", "--no-recommends"]
                if os.getuid() != 0:
                    print("Trying to obtain privileges for installing build dependencies:")
                    sudocheck = ["sudo", "-l"] + pkg_mgr_base
                    status, output = execcmd(*sudocheck, collecter=True, noerror=True)
                    if status:
                        raise Error("%s\nFailed! Cannot proceed without, aborting..."
                                % output.splitlines()[-1])
                    cmd_base = ["sudo"] + pkg_mgr_builddep
                else:
                    cmd_base = pkg_mgr_builddep
                cmd = cmd_base + [spec]
                status, output = execcmd(*cmd, show=verbose, collecter=True, noerror=True)

    status, output = execcmd(*args + ["-b"+build_cmd], show=verbose)
    if svnlog:
        if os.path.isdir(specsdir):
            shutil.rmtree(specsdir)

def create_package(pkgdirurl, log="", verbose=0):
    svn = detectVCS(pkgdirurl)
    tmpdir = tempfile.mktemp()
    try:
        basename = layout.package_name(pkgdirurl)
        if verbose:
            print("Creating package directory...", end=' ')
        sys.stdout.flush()
        ret = svn.mkdir(pkgdirurl,
                        log="Created package directory for '%s'." % basename)
        if verbose:
            print("done")
            print("Checking it out...", end=' ')
        svn.checkout(pkgdirurl, tmpdir)
        if verbose:
            print("done")
            print("Creating package structure...", end=' ')
        svn.mkdir(os.path.join(tmpdir, "current"))
        svn.mkdir(os.path.join(tmpdir, "current", "SPECS"))
        svn.mkdir(os.path.join(tmpdir, "current", "SOURCES"))
        if verbose:
            print("done")
            print("Committing...", end=' ')
        svn.commit(tmpdir,
                   log="Created package structure for '%s'." % basename)
        print("done")
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
    svn = detectVCS(pkgdirurl)
    releasesurl = layout.checkout_url(pkgdirurl, releases=True)
    versionurl = "/".join([releasesurl, version])
    releaseurl = "/".join([versionurl, release])
    currenturl = layout.checkout_url(pkgdirurl)
    if svn.ls(releaseurl, noerror=1):
        raise Error("release already exists")
    svn.mkdir(releasesurl, noerror=1,
              log="Created releases directory.")
    svn.mkdir(versionurl, noerror=1,
              log="Created directory for version %s." % version)
    pristineurl = layout.checkout_url(pkgdirurl, pristine=True)
    svn.remove(pristineurl, noerror=1,
               log="Removing previous pristine/ directory.")
    svn.copy(currenturl, pristineurl,
             log="Copying release %s-%s to pristine/ directory." %
                 (version, release))
    markreleaselog = create_markrelease_log(version, release, revision)
    svn.copy(currenturl, releaseurl, rev=revision,
             log=markreleaselog)

def check_changed(pkgdirurl, all=0, show=0, verbose=0):
    svn = detectVCS(pkgdirurl)
    if all:
        baseurl = pkgdirurl
        packages = []
        if verbose:
            print("Getting list of packages...", end=' ')
            sys.stdout.flush()
        packages = [x[:-1] for x in svn.ls(baseurl)]
        if verbose:
            print("done")
        if not packages:
            raise Error("couldn't get list of packages")
    else:
        baseurl, basename = os.path.split(pkgdirurl)
        packages = [basename]
    clean = []
    changed = []
    nopristine = []
    nocurrent = []
    for package in packages:
        pkgdirurl = os.path.join(baseurl, package)
        current = layout.checkout_url(pkgdirurl)
        pristine = layout.checkout_url(pkgdirurl, pristine=True)
        if verbose:
            print("Checking package %s..." % package, end=' ')
            sys.stdout.flush()
        if not svn.ls(current, noerror=1):
            if verbose:
                print("NO CURRENT")
            nocurrent.append(package)
        elif not svn.ls(pristine, noerror=1):
            if verbose:
                print("NO PRISTINE")
            nopristine.append(package)
        else:
            diff = svn.diff(pristine, current)
            if diff:
                changed.append(package)
                if verbose:
                    print("CHANGED")
                if show:
                    print(diff)
            else:
                if verbose:
                    print("clean")
                clean.append(package)
    if verbose:
        if not packages:
            print("No packages found!")
        elif all:
            print("Total clean packages: %s" % len(clean))
            print("Total CHANGED packages: %d" % len(changed))
            print("Total NO CURRENT packages: %s" % len(nocurrent))
            print("Total NO PRISTINE packages: %s" % len(nopristine))
    return {"clean": clean,
            "changed": changed,
            "nocurrent": nocurrent,
            "nopristine": nopristine}

def checkout(pkgdirurl, path=None, revision=None, branch=None, distro=None, backports=None,
        spec=False):
    o_pkgdirurl = pkgdirurl
    pkgdirurl = layout.package_url(o_pkgdirurl, distro=distro, backports=backports)
    append = None
    if spec:
        append = "SPECS"
    current = layout.checkout_url(pkgdirurl, branch=branch, backports=backports,
            append_path=append)
    if path is None:
        path = layout.package_name(pkgdirurl)
    mirror.info(current, write=True)
    svn = detectVCS(pkgdirurl)
    svn.checkout(current, path, rev=revision, show=1)
    if not spec:
        binrepo.download_binaries(path)
    
def clone(pkgdirurl, path=None, revision=None, branch=None, distro=None, backports=None,
        spec=False, fullnames = True, bindownload = True):
    o_pkgdirurl = pkgdirurl
    pkgdirurl = layout.package_url(o_pkgdirurl, distro=distro, backports=backports)
    append = None
    if spec:
        append = "SPECS"
    current = layout.checkout_url(pkgdirurl, branch=branch, backports=backports,
            append_path=append)
    if path is None:
        path = layout.package_name(pkgdirurl)
    mirror.info(current, write=True)
    git = GIT()
    git.clone(current, path, fullnames=fullnames, show=1)
    if not spec and bindownload:
        binrepo.download_binaries(path)

def getpkgtopdir(basedir=os.path.curdir):
    vcs = detectVCS(basedir)
    if vcs:
        basedir = os.path.relpath(vcs.get_topdir())
        if ispkgtopdir(basedir, vcs_dirname=vcs.vcs_dirname):
            return basedir
    raise Error("can't find top package directories SOURCES and SPECS")

def ispkgtopdir(path=None, vcs_dirname=None):
    if path is None:
        path = os.getcwd()
    names = os.listdir(path)
    if not vcs_dirname:
        vcs = detectVCS(path)
        vcs_dirname = vcs.vcs_dirname
    return (vcs_dirname in names and "SPECS" in names and "SOURCES" in names)

def sync(dryrun=False, commit=False, download=False):
    topdir = getpkgtopdir()
    svn = detectVCS(topdir)
    spath = binrepo.sources_path(topdir)
    binrepoentries = binrepo.parse_sources(spath)
    # run svn info because svn st does not complain when topdir is not an
    # working copy
    svn.info(topdir)
    specsdir = os.path.join(topdir, "SPECS/")
    sourcesdir = os.path.join(topdir, "SOURCES/")
    for path in (specsdir, sourcesdir):
        if not os.path.isdir(path):
            raise Error("%s directory not found" % path)
    specs = glob.glob(os.path.join(specsdir, "*.spec"))
    if not specs:
        raise Error("no .spec files found in %s" % specsdir)
    specpath = specs[0] # FIXME better way?
    try:
        rpm.addMacro("_topdir", os.path.abspath(topdir))
        spec = rpm.TransactionSet().parseSpec(specpath)
    except rpm.error as e:
        raise Error("could not load spec file: %s" % e)
    srclist = spec.sources if isinstance(spec.sources, (list, tuple)) \
            else spec.sources()
    sources = dict((os.path.basename(name), name)
            for name, no, flags in srclist)
    sourcesst = dict((os.path.basename(path), (path, st))
            for st, path in svn.status(sourcesdir, noignore=True))
    toadd = []
    toremove = []
    # add the spec file itself, in case of a new package
    specstl = svn.status(specpath, noignore=True)
    if specstl:
        specst, _ = specstl[0]
        if specst == "?":
            toadd.append(specpath)
    # add source files:
    for source, url in sources.items():
        sourcepath = os.path.join(sourcesdir, source)
        if sourcesst.get(source):
            if not (source in binrepoentries) and sourcesst.get(source)[1] == '?':
                toadd.append(sourcepath)
        elif not download and not os.path.isfile(sourcepath):
            sys.stderr.write("warning: %s not found\n" % sourcepath)
        elif download and not os.path.isfile(sourcepath):
            print("%s not found, downloading from %s" % (sourcepath, url))
            fmt = config.get("global", "download-command",
                    "wget -c -O '$dest' $url")
            context = {"dest": sourcepath, "url": url}
            try:
                cmd = string.Template(fmt).substitute(context)
            except KeyError as e:
                raise Error("invalid variable %r in download-command "\
                        "configuration option" % e)
            try:
                status, output = execcmd(cmd, show=True)
            except Error as e:
                os.unlink(sourcepath)
                raise Error("Could not download file %s\n" % url)

            if os.path.isfile(sourcepath):
                toadd.append(sourcepath)
            else:
                raise Error("file not found: %s" % sourcepath)
    # rm entries not found in sources and still in svn
    found = os.listdir(sourcesdir)
    for entry in found:
        if entry == ".svn" or entry == binrepo.SOURCES_FILE:
            continue
        status = sourcesst.get(entry)
        path = os.path.join(sourcesdir, entry)
        if entry not in sources:
            if status is None or entry in binrepoentries:
                toremove.append(path)
    for path in toremove:
        print("D\t%s" % path)
        if not dryrun:
            delete([path], commit=commit)
    for path in toadd:
        print("A\t%s" % path)
        if not dryrun:
            upload([path], commit=commit)

def commit(target=".", message=None, logfile=None):
    svn = detectVCS(target)
    status = svn.status(target, quiet=True)
    if not status:
        print("nothing to commit")
        return
    info = svn.info2(target)
    url = info.get("URL")
    if url is None:
        raise Error("working copy URL not provided by svn info")
    mirrored = mirror.using_on(url)
    if mirrored:
        newurl = mirror.switchto_parent(svn, url, target)
        print("relocated to", newurl)
    # we can't use the svn object here because svn --non-interactive option
    # hides VISUAL
    opts = []
    if message is not None:
        opts.append("-m \"%s\"" % message)
    if logfile is not None:
        opts.append("-F \"%s\"" % logfile)
    mopts = " ".join(opts)
    os.system("svn ci %s %s" % (mopts, target))
    if mirrored:
        print("use \"mgarepo switch\" in order to switch back to mirror "\
                "later")

def spec_sources(topdir):
    specs = glob.glob(os.path.join(topdir, "SPECS/*.spec"))
    spec_path = specs[0] # FIXME use svn info to ensure which one
    ts = rpm.ts()
    spec = ts.parseSpec(spec_path)
    sources = [name for name, x, y in spec.sources()]
    return sources
    
def update(target=None):
    vcs = None
    info = None
    vcs_target = None
    br_target = None
    if target:
        vcs_target = target
    else:
        top = getpkgtopdir()
        vcs_target = top
        br_target = top
    if vcs_target:
        vcs = detectVCS(vcs_target)
        vcs.update(vcs_target, show=True)
    if br_target:
        if not vcs:
            vcs = detectVCS(br_target)
        info = vcs.info2(vcs_target) 
        if not br_target and not vcs_target:
            raise Error("target not in %s nor in binaries "\
                    "repository: %s" % (type(vcs).__name__,target))
        url = info["URL"]
        binrepo.download_binaries(br_target)

def upload(paths, commit=False):
    topdir = getpkgtopdir()
    svn = detectVCS(topdir)
    for path in paths:
        if os.path.isdir(path) or binrepo.is_binary(path):
            binrepo.upload_binary(topdir, os.path.basename(path))
            binrepo.update_sources(topdir, added=[path])
            if commit:
                silent = config.get("log", "ignore-string", "SILENT")
                message = "%s: new file %s" % (silent, path)
                svn.commit(binrepo.sources_path(topdir), log=message)
        else:
            svn.add(path, local=True)
            if commit:
                silent = config.get("log", "ignore-string", "SILENT")
                message = "%s: new file %s" % (silent, path)
                svn.commit(path, log=message)

def delete(paths, commit=False):
    silent = config.get("log", "ignore-string", "SILENT")
    topdir = getpkgtopdir()
    svn = detectVCS(topdir)
    for path in paths:
        message = "%s: delete file %s" % (silent, path)
        if binrepo.is_binary(path):
            binrepo.update_sources(topdir, removed=[os.path.basename(path)])
            if commit:
                svn.commit(binrepo.sources_path(topdir), log=message)
        else:
            svn.remove(path, local=True)
            if commit:
                svn.commit(path, log=message)

def obsolete(pkgdirurl, branch=None, distro=None, backports=None, commit=False, log=None):
    o_pkgdirurl = pkgdirurl
    pkgdirurl = layout.package_url(o_pkgdirurl, distro=distro, backports=backports)
    pkgdest = layout.package_url(o_pkgdirurl, obsolete=True, backports=backports)
    svn = detectVCS(pkgdirurl)
    svn.mv(pkgdirurl, pkgdest, message=log)
    if commit:
        svn.commit(path, log=log)

def switch(mirrorurl=None):
    svn  = SVN()
    topdir = getpkgtopdir()
    info = svn.info2(topdir)
    wcurl = info.get("URL")
    if wcurl is None:
        raise Error("working copy URL not provided by svn info")
    newurl = mirror.autoswitch(svn, topdir, wcurl, mirrorurl)
    print("switched to", newurl)

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
        raise Error("SPECS and/or SOURCES directories not found")

    # Then, check if this is really a subversion directory.
    if not os.path.isdir(os.path.join(path, ".svn")):
        raise Error("subversion directory not found")
    
    svn = detectVCS(path)

    # Now, extract the package name.
    info = svn.info2(path)
    url = info.get("URL")
    if url is None:
        raise Error("missing URL from svn info %s" % path)
    toks = url.split("/")
    if len(toks) < 2 or toks[-1] != "current":
        raise Error("unexpected URL received from 'svn info'")
    name = toks[-2]
    url = "/".join(toks[:-1])

    # Finally, guess revision.
    max = -1
    files = []
    files.extend(glob.glob("%s/*" % specsdir))
    files.extend(glob.glob("%s/*" % sourcesdir))
    for file in files:
        try:
            info = svn.info2(file)
        except Error:
            # possibly not tracked
            continue
        if info is None:
            continue
        rawrev = info.get("Last Changed Rev")
        if rawrev:
            rev = int(rawrev)
            if rev > max:
                max = rev
    if max == -1:
        raise Error("revision tag not found in 'svn info' output")

    if mirror.using_on(url):
        url = mirror.switchto_parent_url(url)
    
    return name, url, max

def get_pkg_tag(tag, path=os.path.curdir, subpkg=None):
    topdir = getpkgtopdir(path)
    speclist = glob.glob(os.path.join(topdir, "SPECS", "*.spec"))
    if not speclist:
        raise Error("no spec files found")
    specfile = speclist[0]

    pkg = rpm.spec(specfile)
    if subpkg is None:
        header = pkg.sourceHeader
    elif isinstance(subpkg,int):
        header = pkg.packages(subpkg)
    else:
        raise Error("Subpkg must be the index number of a package,"\
                "or None for source package")

    if isinstance(header[tag],bytes):
        return header[tag].decode("utf8")
    else:
        return header[tag]

# vim:et:ts=4:sw=4
