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
    vcs_dirname = ".git"
    def __init__(self):
        VCS.__init__(self)
        self.vcs_name = "git"
        self.vcs_command = config.get("global", "git-command", ["git", "svn"])
        self.vcs_supports['clone'] = True
        self.env_defaults = {"GIT_SSH": self.vcs_wrapper}

    def clone(self, url, targetpath, **kwargs):
        if url.split(':')[0].find("svn") < 0:
            return VCS.clone(self, url, targetpath, **kwargs)
        else:
            # To speed things up on huge repositories, we'll just grab all the
            # revision numbers for this specific directory and grab these only
            # in stead of having to go through each and every revision...
            cmd = ["svn", "log", "-g", "--xml", url]
            retval, result = execcmd(*cmd)
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
            # cloning svn braches as well should rather be optionalif reenabled..
            #cmd = ["init", topurl, "--trunk="+trunk, "--tags="+tags, targetpath]
            cmd = ["init", url, targetpath]
            self._execVcs(*cmd, **kwargs)
            chdir(targetpath)
            revisions.sort()
            for entry in logentries:
                revisions.append(int(entry.attrib["revision"]))
            revisions.sort()
            while revisions:
                cmd = ["fetch", "--log-window-size=1000", "-r%d" % revisions.pop(0)]
                self._execVcs(*cmd, **kwargs)
            cmd = ["rebase", "--log-window-size=1000", "--local", "--fetch-all", "git-svn"]
            return self._execVcs_success(*cmd, **kwargs)

    def update(self, path, **kwargs):
        cmd = ["log", "--oneline", "--limit=1"]
        retval, result = self._execVcs(*cmd)
        if retval:
            return retval

        revision = result.split()

        if revision[0][0] == 'r':
            startrev = "-r"+str(int(revision[0][1:])+1)
        else:
            startrev = "BASE"

        cmd = ["propget", "svn:entry:committed-rev"]
        retval, lastrev = self._execVcs(*cmd)
        if retval:
            return retval

        cmd = ["git", "config", "--get-regexp", '^svn-remote.svn.(url|fetch)']
        retval, result = execcmd(*cmd)
        if retval:
            return retval
        result = result.strip().split()
        url = result[1] + "/" + result[3].split(":")[0]

        # To speed things up on huge repositories, we'll just grab all the
        # revision numbers for this specific directory and grab these only
        # in stead of having to go through each and every revision...
        cmd = ["svn", "log", "-g", "--xml", "%s:%s" % (startrev,lastrev), url]
        retval, result = execcmd(*cmd)
        if retval:
            return retval
        parser = ElementTree.XMLParser()
        result = "".join(result.split("\n"))
        parser.feed(result)
        log = parser.close()
        logentries = log.getiterator("logentry")
        revisions = []
        chdir(path)
        for entry in logentries:
            revisions.append(int(entry.attrib["revision"]))
        revisions.sort()
        while revisions:
            cmd = ["fetch", "--log-window-size=1000", "-r%d" % revisions.pop(0)]
            self._execVcs(*cmd, **kwargs)

        cmd = ["rebase", "--log-window-size=1000", "--local", "--fetch-all", "git-svn"]
        status, output = self._execVcs(*cmd, **kwargs)
        if status == 0:
            return [x.split() for x in output.split()]
        return None


class SVNLook(VCSLook):
    def __init__(self, repospath, txn=None, rev=None):
        VCSLook.__init__(self, repospath, txn, rev)

# vim:et:ts=4:sw=4
