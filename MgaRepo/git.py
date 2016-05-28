from MgaRepo import Error, config
from MgaRepo.util import execcmd
from MgaRepo.VCS import *
from os.path import basename, dirname
from os import chdir, getcwd
import sys
import re
import time
from xml.etree import ElementTree
import subprocess

class GITLogEntry(VCSLogEntry):
    def __init__(self, revision, author, date):
        VCSLogEntry.__init__(self, revision, author, data)

class GIT(VCS):
    def __init__(self):
        VCS.__init__(self)
        self.vcs_name = "git"
        self.vcs_command = config.get("global", "git-command", "git")
        self.vcs_supports['clone'] = True
        self.env_defaults = {"GIT_SSH": self.vcs_wrapper}

    def clone(self, url, targetpath, **kwargs):
        if url.split(':')[0].find("svn") < 0:
            return VCS.clone(self, url, targetpath, **kwargs)
        else:
            # To speed things up on huge repositories, we'll just grab all the
            # revision numbers for this specific directory and grab these only
            # in stead of having to go through each and every revision...
            retval, result = execcmd("svn log --stop-on-copy --xml %s" % url)
            if retval:
                return retval
            parser = ElementTree.XMLParser()
            result = "".join(result.split("\n"))
            parser.feed(result)
            log = parser.close()
            logentries = log.getiterator("logentry")
            revisions = []
            topurl = dirname(url)
            trunk = basename(url)
            tags = "releases"
            execcmd("git svn init %s --trunk=%s --tags=%s %s" % (topurl, trunk, tags, targetpath), show=True)
            chdir(targetpath)
            for entry in logentries:
                revisions.append(entry.attrib["revision"])
            while revisions:
                execcmd("git svn fetch --log-window-size=1000 -r%d" % int(revisions.pop()), show=True)

            cmd = ["svn", "rebase"]
            return self._execVcs_success(*cmd, **kwargs)

class SVNLook(VCSLook):
    def __init__(self, repospath, txn=None, rev=None):
        VCSLook.__init__(self, repospath, txn, rev)

# vim:et:ts=4:sw=4
