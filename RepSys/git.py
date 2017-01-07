from RepSys import Error, config
from RepSys.util import execcmd
from RepSys.VCS import *
from RepSys.svn import SVN
from RepSys.log import UserTagParser
from os.path import basename, dirname, abspath, lexists, join
from os import chdir, getcwd
from tempfile import mkstemp
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
    vcs_name = "git"
    def __init__(self, path=None, url=None):
        VCS.__init__(self, path, url)
        vcs = getattr(VCS, "vcs")
        vcs.append((self.vcs_name, self.vcs_dirname))
        setattr(VCS,"vcs", vcs)
        self.vcs_command = config.get("global", "git-command", ["git"])
        self.vcs_supports['clone'] = True
        self.env_defaults = {"GIT_SSH": self.vcs_wrapper}

    def verifyrepo(self):
        cmd = ["ls-remote", "-h", self.url, "refs/heads/master"]
        status, output = self._execVcs(*cmd, shownoerror=True)
        if status != 0:
            raise Error("repository %s doesn't exist: %s" % (self.url))

    def configget(self, key="", location="--local"):
        cmd = ["config", location, "--get-regexp", key]
        config = None
        status, output = self._execVcs(*cmd, noerror=True)
        if not status and output:
            config = eval("{'" + output.replace("\n", "',\n'").replace(" ", "' : '") + "'}")
        return config

    def configset(self, config, location="--local"):
        cmd = ("config", location)
        for pair in config.items():
            status, output = self._execVcs(*cmd + pair)
            if status:
                return False
        return True

    def clone(self, url=None, targetpath=None, fullnames=True, **kwargs):
        self.verifyrepo()
        return VCS.clone(self, show=True, **kwargs)

    def status(self, path, **kwargs):
        cmd = ["status", "--porcelain", path + '@' if '@' in path else path]
        if kwargs.get("verbose"):
            cmd.append("-v")
        if kwargs.get("noignore"):
            cmd.append("--ignored")
        if kwargs.get("quiet"):
            cmd.append("-uno")
        else:
            cmd.append("-uall")
        status, output = self._execVcs(*cmd, **kwargs)
        if status == 0:
            return [(x[0], x[8:]) for x in output.splitlines()]
        return None

    def remote(self, *args, **kwargs):
        cmd = ["remote"] + list(args)
        status, output = self._execVcs(*cmd, **kwargs)
        return status, output

    def pull(self, *args, **kwargs):
        cmd = ["pull"] + list(args)
        status, output = self._execVcs(*cmd, **kwargs)
        return status, output

    def push(self, *args, **kwargs):
        cmd = ["push"] + list(args)
        status, output = self._execVcs(*cmd, **kwargs)
        return status, output

class GITLook(VCSLook):
    def __init__(self, repospath, txn=None, rev=None):
        VCSLook.__init__(self, repospath, txn, rev)

# vim:et:ts=4:sw=4
