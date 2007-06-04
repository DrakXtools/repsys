import os
import urlparse

from RepSys import config
from RepSys.svn import SVN

def relocate_path(oldparent, newparent, url):
    subpath = url[len(oldparent)-1:]
    newurl = newparent + "/" + subpath # subpath usually gets / at begining
    return newurl

def enabled():
    mirror = config.get("global", "mirror")
    default_parent = config.get("global", "default_parent")
    return (mirror is not None and 
            default_parent is not None)

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
