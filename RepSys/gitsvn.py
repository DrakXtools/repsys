from RepSys import Error, config
from RepSys.util import execcmd
from RepSys.VCS import *
from RepSys.GIT import *
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

class GITSVN(GIT):
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

    def clone(self, url=None, targetpath=None, fullnames=True, **kwargs):
        if not VCS.clone(url, targetpath, **kwargs):
            self.init(url, targetpath, fullnames=True, **kwargs)
            if not GIT.clone(self, url, targetpath, fullnames, **kwargs):
                return self.update(targetpath, clone=True, **kwargs)

    def init(self, url, targetpath, fullnames=True, branch=None, **kwargs):
        # verify repo url
        execcmd("svn", "info", url)

        topurl = dirname(url)
        trunk = basename(url)
        tags = "releases"
        # cloning svn braches as well should rather be optionalif reenabled..
        #cmd = ["svn", "init", topurl, "--trunk="+trunk, "--tags="+tags", targetpath]

        cmd = ["svn", "init", url, abspath(targetpath)]
        self._execVcs(*cmd, **kwargs)
        os.environ.update({"GIT_WORK_TREE" : abspath(targetpath), "GIT_DIR" : join(abspath(targetpath),".git")})

        if fullnames:
            usermap = UserTagParser()
            # store configuration in local git config so that'll be reused later when ie. updating
            gitconfig = {"svn-remote.authorlog.url" : usermap.url,
                    "svn-remote.authorlog.defaultmail": usermap.defaultmail}
            self.configset(gitconfig)

        if branch:
            execcmd(("git", "init", "-q", self.path), **kwargs)
            execcmd(("git", "checkout", "-q", branch), **kwargs)
            cmd = ["svn", "rebase", "--local"]
            status, output = self._execVcs(*cmd, **kwargs)

        return True

    def info(self, path, **kwargs):
        cmd = ["svn", "info", path + '@' if '@' in path else path]
        status, output = self._execVcs(local=True, noerror=True, *cmd, **kwargs)
        if (("Not a git repository" not in output) and \
                ("Unable to determine upstream SVN information from working tree history" not in output)):
            return output.splitlines()
        return None

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

    def update(self, targetpath, clone=False, **kwargs):
        os.environ.update({"GIT_WORK_TREE" : abspath(targetpath), "GIT_DIR" : join(abspath(targetpath),".git")})

        if not clone:
            cmd = ["svn", "log", "--oneline", "--limit=1"]
            retval, result = self._execVcs(*cmd)
            if retval:
                return retval

            revision = result.split()

            if revision[0][0] == 'r':
                startrev = "-r"+str(int(revision[0][1:])+1)
            else:
                startrev = "BASE"

            cmd = ["svn", "propget", "svn:entry:committed-rev"]
            retval, lastrev = self._execVcs(*cmd)
            if retval:
                return retval

        #cmd = ["config", "--get-regexp", '^svn-remote.svn.(url|fetch)']
        cmd = ["config", "--get", "svn-remote.svn.url"]
        retval, result = self._execVcs(*cmd)
        if retval:
            return retval

        #result = result.strip().split()
        #url = result[1] + "/" + result[3].split(":")[0]
        url = result.strip()

        # To speed things up on huge repositories, we'll just grab all the
        # revision numbers for this specific directory and grab these only
        # in stead of having to go through each and every revision...
        cmd = ["svn", "log", "-g", "--xml", url]
        if not clone:
            cmd.append("%s:%s" % (startrev,lastrev))
        retval, result = execcmd(*cmd)
        if retval:
            return retval

        xmllog = ElementTree.fromstring(result)
        logentries = xmllog.getiterator("logentry")
        revisions = []
        for entry in logentries:
            revisions.append(int(entry.attrib["revision"]))
        revisions.sort()

        fetchcmd = ["svn", "fetch", "--log-window-size=1000"]
        gitconfig = self.configget("svn-remote.authorlog")
        if gitconfig:
            usermap = UserTagParser(url=gitconfig.get("svn-remote.authorlog.url"),defaultmail=gitconfig.get("svn-remote.authorlog.defaultmail"))
            usermapfile = usermap.get_user_map_file()
            fetchcmd.extend(("--authors-file", usermapfile))
        fetchcmd.append("")

        while revisions:
            fetchcmd[-1] = "-r%d"%revisions.pop(0)
            self._execVcs(*fetchcmd, **kwargs)
        if gitconfig:
            usermap.cleanup()

        cmd = ["svn", "rebase", "--log-window-size=1000", "--local", "--fetch-all", "git-svn"]
        status, output = self._execVcs(*cmd, **kwargs)
        if status == 0:
            return [x.split() for x in output.split()]
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

# vim:et:ts=4:sw=4
