import sys
import os
import urlparse
import urllib

from RepSys import Error, config, layout
from RepSys.svn import SVN

def mirror_url():
    mirror = config.get("global", "mirror")
    return mirror

def normalize_path(url):
    """normalize url for relocate_path needs"""
    parsed = urlparse.urlparse(url)
    path = os.path.normpath(parsed[2])
    newurl = urlparse.urlunparse((parsed[0], parsed[1], path,
        parsed[3], parsed[4], parsed[5]))
    return newurl

def _joinurl(url, relpath):
    parsed = urlparse.urlparse(url)
    newpath = os.path.join(parsed[2], relpath)
    newurl = urlparse.urlunparse((parsed[0], parsed[1], newpath,
        parsed[3], parsed[4], parsed[5]))
    return newurl


def strip_username(url):
    parsed = list(urlparse.urlparse(url))
    _, parsed[1] = urllib.splituser(parsed[1])
    newurl = urlparse.urlunparse(parsed)
    return newurl

def same_base(parent, url):
    """returns true if parent is parent of url"""
    parent = normalize_path(parent)
    url = normalize_path(url)
    url = strip_username(url)
    return url.startswith(parent)

def relocate_path(oldparent, newparent, url):
    oldparent = normalize_path(oldparent)
    newparent = normalize_path(newparent)
    url = normalize_path(url)
    subpath = url[len(oldparent)+1:]
    newurl = _joinurl(newparent,  subpath) # subpath usually gets / at begining
    return newurl

def enabled(wcurl=None):
    mirror = mirror_url()
    repository = layout.repository_url()
    enabled = False
    if mirror and repository:
        enabled = True
        if wcurl and not same_base(mirror, wcurl):
            enabled = False
    return enabled

def using_on(url):
    """returnes True if the URL points to the mirror repository"""
    mirror = mirror_url()
    if mirror:
        using = same_base(mirror, url)
    else:
        using = False
    return using

def info(url, stream=sys.stderr):
    if using_on(url):
        stream.write("using mirror\n")

def mirror_relocate(oldparent, newparent, url, wcpath):
    svn = SVN()
    newurl = relocate_path(oldparent, newparent, url)
    svn.switch(newurl, url, path=wcpath, relocate=True)
    return newurl

def switchto_parent(svn, url, path):
    """Relocates the working copy to default_parent"""
    newurl = mirror_relocate(mirror_url(), layout.repository_url(), url, path)
    return newurl

def switchto_parent_url(url):
    newurl = relocate_path(mirror_url(), layout.repository_url(), url)
    return newurl

def switchto_mirror(svn, url, path):
    newurl = mirror_relocate(layout.repository_url(), mirror_url(), url, path)
    return newurl

def autoswitch(svn, wcpath, wcurl, newbaseurl=None):
    """Switches between mirror, default_parent, or newbaseurl"""
    nobase = False
    mirror = mirror_url()
    repository = layout.repository_url()
    current = repository
    if repository is None:
        raise Error, "the option repository from repsys.conf is "\
                "required"
    indefault = same_base(repository, wcurl)
    if not newbaseurl:
        if not mirror:
            raise Error, "an URL is needed when the option mirror "\
                    "from repsys.conf is not set"
        if indefault:
            chosen = mirror
        elif same_base(mirror, wcurl):
            current = mirror
            chosen = repository
        else:
            nobase = True
    else:
        if mirror and same_base(mirror, wcurl):
            current = mirror
        elif indefault:
            pass # !!!!
        else:
            nobase = True
        chosen = newbaseurl
    if nobase:
        raise Error, "the URL of this working copy is not based in "\
                "repository nor mirror URLs"
    assert current != chosen
    newurl = mirror_relocate(current, chosen, wcurl, wcpath)
    return newurl
