from RepSys.util import execcmd
from RepSys.VCS import *
import sys
import os
import re
import time

__all__ = ["SVN", "SVNLook", "SVNLogEntry"]

class SVNLogEntry(VCSLogEntry):
    def __init__(self, revision, author, date):
        VCSLogEntry.__init__(self, revision, author, data)

class SVN(VCS):
    vcs_dirname = ".svn"
    vcs_name = "svn"
    def __init__(self, path=None, url=None):
        VCS.__init__(self, path, url)
        vcs = getattr(VCS, "vcs")
        vcs.append((self.vcs_name, self.vcs_dirname))
        setattr(VCS,"vcs", vcs)
        self.vcs_command = config.get("global", "svn-command", ["svn"])
        self.env_defaults = {"SVN_SSH": self.vcs_wrapper}

    def drop_ssh_if_no_auth(self, url):
        if url and url.startswith("svn+ssh://"):
            cmd = ["info", "--non-interactive", "--no-newline", "--show-item", "url", url]
            status, output = self._execVcs(*cmd, local=True, noerror=True, show=False)
            if status == 1 and (("E170013" in output) or ("E210002" in output)):
                url = url.replace("svn+ssh://", "svn://")
                status, output = self._execVcs(*cmd, local=True, noerror=True, show=False)
                if status == 0 and output == url:
                    pass
        return url

class SVNLook(VCSLook):
    def __init__(self, repospath, txn=None, rev=None):
        VCSLook.__init__(self, repospath, txn, rev)
        self.execcmd = "svnlook"

# vim:et:ts=4:sw=4
