import os
import urlparse

from RepSys import config
from RepSys.svn import SVN

def _normdirurl(url):
    """normalize url for relocate_path needs"""
    parsed = urlparse.urlparse(url)
    path = os.path.normpath(parsed.path)
    path += "/" # assuming we always deal with directories
    newurl = urlparse.urlunparse((parsed.scheme, parsed.netloc, path,
        parsed.params, parsed.query, parsed.fragment))
    return newurl

def _joinurl(url, relpath):
    parsed = urlparse.urlparse(url)
    newpath = os.path.join(parsed.path, relpath)
    newurl = urlparse.urlunparse((parsed.scheme, parsed.netloc, newpath,
        parsed.params, parsed.query, parsed.fragment))
    return newurl

def same_base(parent, url):
    """returns true if parent is parent of url"""
    parent = _normdirurl(parent)
    url = _normdirurl(url)
    #FIXME handle paths with/without username/password
    return url.startswith(parent)

def relocate_path(oldparent, newparent, url):
    oldparent = _normdirurl(oldparent)
    newparent = _normdirurl(newparent)
    url = _normdirurl(url)
    subpath = url[len(oldparent):]
    newurl = _joinurl(newparent,  subpath) # subpath usually gets / at begining
    return newurl

def enabled(wcurl=None):
    mirror = config.get("global", "mirror")
    default_parent = config.get("global", "default_parent")
    enabled = False
    if mirror and default_parent:
        enabled = True
        if wcurl and (not same_base(mirror, wcurl)):
            enabled = False
    return enabled

def mirror_relocate(oldparent, newparent, url, wcpath):
    svn = SVN(noauth=True)
    newurl = relocate_path(oldparent, newparent, url)
    svn.switch(newurl, url, path=wcpath, relocate="True")
    return newurl

def switchto_parent(svn, url, path):
    """Relocates the working copy to default_parent"""
    mirror = config.get("global", "mirror")
    default_parent = config.get("global", "default_parent")
    newurl = mirror_relocate(mirror, default_parent, url, path)
    return newurl

def switchto_mirror(svn, url, path):
    mirror = config.get("global", "mirror")
    default_parent = config.get("global", "default_parent")
    newurl = mirror_relocate(default_parent, mirror, url, path)
    return newurl

def checkout_url(url):
    mirror = config.get("global", "mirror")
    default_parent = config.get("global", "default_parent")
    if mirror is not None and default_parent is not None:
        return relocate_path(default_parent, mirror, url)
    return url

def autoswitch(svn, wcpath, wcurl, newbaseurl=None):
    """Switches between mirror, default_parent, or newbaseurl"""
    nobase = False
    mirror = config.get("global", "mirror")
    default_parent = config.get("global", "default_parent")
    current = default_parent
    if default_parent is None:
        raise Error, "the option default_parent from repsys.conf is "\
                "required"
    indefault = same_base(default_parent, wcurl)
    if not newbaseurl:
        if not mirror:
            raise Error, "an URL is needed when the option mirror "\
                    "from repsys.conf is not set"
        if indefault:
            chosen = mirror
        elif same_base(mirror, wcurl):
            current = mirror
            chosen = default_parent
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
                "default_parent nor mirror URLs"
    assert current != chosen
    newurl = mirror_relocate(current, chosen, wcurl, wcpath)
    return newurl
