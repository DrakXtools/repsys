#!/usr/bin/python
import re
import os
import tempfile

import ConfigParser

config = ConfigParser.Config()
tempfile.tempdir = config.get("submit", "tempdir", None) or None # when ""
del ConfigParser

class Error(Exception): pass

class RepSysTree:
    """
    This class just hold methods that abstract all the not-so-explicit
    rules about the directory structure of a repsys repository.
    """
    def fixpath(cls, url):
        return re.sub("/+$", "", url)
    fixpath = classmethod(fixpath)

    def pkgname(cls, pkgdirurl):
        # we must remove trailling slashes in the package path because
        # os.path.basename could return "" from URLs ending with "/"
        fixedurl = cls.fixpath(pkgdirurl)
        return os.path.basename(fixedurl)
    pkgname = classmethod(pkgname)
            
# vim:et:ts=4:sw=4
