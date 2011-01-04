""" Handles repository layout scheme and package URLs."""

import os
import urlparse

from RepSys import Error, config
from RepSys.svn import SVN

__all__ = ["package_url", "checkout_url", "repository_url", "get_url_revision"]

def layout_dirs():
    devel_branch = config.get("global", "trunk-dir", "cooker/")
    devel_branch = os.path.normpath(devel_branch)
    branches_dir = config.get("global", "branches-dir", "updates/")
    branches_dir = os.path.normpath(branches_dir)
    return devel_branch, branches_dir

def get_url_revision(url, retrieve=True):
    """Get the revision from a given URL

    If the URL contains an explicit revision number (URL@REV), just use it
    without even checking if the revision really exists.

    The parameter retrieve defines whether it must ask the SVN server for
    the revision number or not when it is not found in the URL.
    """
    url, rev = split_url_revision(url)
    if rev is None and retrieve:
        # if no revspec was found, ask the server
        svn = SVN()
        rev = svn.revision(url)
    return rev

def unsplit_url_revision(url, rev):
    if rev is None:
        newurl = url
    else:
        parsed = list(urlparse.urlparse(url))
        path = os.path.normpath(parsed[2])
        parsed[2] = path + "@" + str(rev)
        newurl = urlparse.urlunparse(parsed)
    return newurl

def split_url_revision(url):
    """Returns a tuple (url, rev) from an subversion URL with @REV
    
    If the revision is not present in the URL, rev is None.
    """
    parsed = list(urlparse.urlparse(url))
    path = os.path.normpath(parsed[2])
    dirs = path.rsplit("/", 1)
    lastname = dirs[-1]
    newname = lastname
    index = lastname.rfind("@")
    rev = None
    if index != -1:
        newname = lastname[:index]
        rawrev = lastname[index+1:]
        if rawrev:
            try:
                rev = int(rawrev)
                if rev < 0:
                    raise ValueError
            except ValueError:
                raise Error, "invalid revision specification on URL: %s" % url
    dirs[-1] = newname
    newpath = "/".join(dirs)
    parsed[2] = newpath
    newurl = urlparse.urlunparse(parsed)
    return newurl, rev

def checkout_url(pkgdirurl, branch=None, version=None, release=None,
        releases=False, pristine=False, append_path=None):
    """Get the URL of a branch of the package, defaults to current/
    
    It tries to preserve revisions in the format @REV.
    """
    parsed = list(urlparse.urlparse(pkgdirurl))
    path, rev = split_url_revision(parsed[2])
    if releases:
        path = os.path.normpath(path + "/releases")
    elif version:
        assert release is not None
        path = os.path.normpath(path + "/releases/" + version + "/" + release)
    elif pristine:
        path = os.path.join(path, "pristine")
    elif branch:
        path = os.path.join(path, "branches", branch)
    else:
        path = os.path.join(path, "current")
    if append_path:
        path = os.path.join(path, append_path)
    path = unsplit_url_revision(path, rev)
    parsed[2] = path
    newurl = urlparse.urlunparse(parsed)
    return newurl

def convert_default_parent(url):
    """Removes the cooker/ component from the URL"""
    parsed = list(urlparse.urlparse(url))
    path = os.path.normpath(parsed[2])
    rest, last = os.path.split(path)
    parsed[2] = rest
    newurl = urlparse.urlunparse(parsed)
    return newurl

def remove_current(pkgdirurl):
    parsed = list(urlparse.urlparse(pkgdirurl))
    path = os.path.normpath(parsed[2])
    rest, last = os.path.split(path)
    if last == "current":
        # FIXME this way we will not allow packages to be named "current"
        path = rest
    parsed[2] = path
    newurl = urlparse.urlunparse(parsed)
    return newurl

def repository_url(mirrored=False):
    url = None
    if mirrored and config.getbool("global", "use-mirror", "yes"):
        url = config.get("global", "mirror")
    if url is None:
        url = config.get("global", "repository")
        if not url:
            # compatibility with the default_parent configuration option
            default_parent = config.get("global", "default_parent")
            if default_parent is None:
                raise Error, "you need to set the 'repository' " \
                        "configuration option on repsys.conf"
            url = convert_default_parent(default_parent)
    return url

def package_url(name_or_url, version=None, release=None, distro=None,
        mirrored=True):
    """Returns a tuple with the absolute package URL and its name

    @name_or_url: name, relative path, or URL of the package. In case it is
                  a URL, the URL will just be 'normalized'.
    @version: the version to be fetched from releases/ (requires release)
    @release: the release number to be fetched from releases/$version/
    @distro: the name of the repository branch inside updates/
    @mirrored: return an URL based on the mirror repository, if enabled
    """
    from RepSys import mirror
    if "://" in name_or_url:
        pkgdirurl = mirror.normalize_path(name_or_url)
        pkgdirurl = remove_current(pkgdirurl)
        if mirror.using_on(pkgdirurl) and not mirrored:
            pkgdirurl = mirror.relocate_path(mirror.mirror_url(),
                    repository_url(), pkgdirurl)
    else:
        name = name_or_url
        devel_branch, branches_dir = layout_dirs()
        if distro or "/" in name:
            default_branch = branches_dir
            if distro:
                default_branch = os.path.join(default_branch, distro)
        else:
            default_branch = devel_branch # cooker
        path = os.path.join(default_branch, name)
        parsed = list(urlparse.urlparse(repository_url(mirrored=mirrored)))
        parsed[2] = os.path.join(parsed[2], path)
        pkgdirurl = urlparse.urlunparse(parsed)
    return pkgdirurl

def package_name(pkgdirurl):
    """Returns the package name from a package URL
    
    It takes care of revision numbers"""
    parsed = urlparse.urlparse(pkgdirurl)
    path, rev = split_url_revision(parsed[2])
    rest, name = os.path.split(path)
    return name

def package_spec_url(pkgdirurl, *args, **kwargs):
    """Returns the URL of the specfile of a given package URL

    The parameters are the same used by checkout_url, except append_path.
    """
    kwargs["append_path"] = "SPECS/" + package_name(pkgdirurl) + ".spec"
    specurl = checkout_url(pkgdirurl, *args, **kwargs)
    return specurl

def distro_branch(pkgdirurl):
    """Tries to guess the distro branch name from a package URL"""
    from RepSys.mirror import same_base
    found = None
    repo = repository_url()
    if same_base(repo, pkgdirurl):
        devel_branch, branches_dir = layout_dirs()
        repo_path = urlparse.urlparse(repo)[2]
        devel_path = os.path.join(repo_path, devel_branch)
        branches_path = os.path.join(repo_path, branches_dir)
        parsed = urlparse.urlparse(pkgdirurl)
        path = os.path.normpath(parsed[2])
        if path.startswith(devel_path):
            # devel_branch must be before branches_dir in order to allow
            # devel_branch to be inside branches_dir, as in /branches/cooker
            _, found = os.path.split(devel_branch)
        elif path.startswith(branches_path):
            comps = path.split("/")
            if branches_path == "/":
                found = comps[1]
            elif len(comps) >= 2: # must be at least branch/pkgname
                found = comps[branches_path.count("/")+1]
    return found

