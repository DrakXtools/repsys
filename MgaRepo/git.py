from MgaRepo import Error, config
from MgaRepo.util import execcmd
from MgaRepo.VCS import *
from MgaRepo.svn import SVN
from MgaRepo.log import UserTagParser
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
    def __init__(self, path=os.path.curdir):
        VCS.__init__(self, path)
        self.vcs_command = config.get("global", "git-command", ["git"])
        self.vcs_supports['clone'] = True
        self.env_defaults = {"GIT_SSH": self.vcs_wrapper}

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

    def clone(self, url, targetpath, fullnames=True, **kwargs):
        for vcs in (SVN, GIT):
            if lexists(join(targetpath, vcs.vcs_dirname)):
                raise Error("target path %s already contains %s repository, aborting..." % (targetpath, vcs.vcs_name))

        self.init(url, targetpath, fullnames=True, **kwargs)
        if url.split(':')[0].find("svn") < 0:
            return VCS.clone(self, url, **kwargs)
        else:
            return self.update(targetpath, clone=True, **kwargs)

    def init(self, url, targetpath, fullnames=True, **kwargs):
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

        return True

    def info(self, path, **kwargs):
        cmd = ["svn", "info", path + '@' if '@' in path else path]
        status, output = self._execVcs(local=True, noerror=True, *cmd, **kwargs)
        if (("Not a git repository" not in output) and \
                ("Unable to determine upstream SVN information from working tree history" not in output)):
            return output.splitlines()
        return None

    def status(self, path, **kwargs):
        cmd = ["status", path + '@' if '@' in path else path]
        if kwargs.get("verbose"):
            cmd.append("-v")
        if kwargs.get("noignore"):
            cmd.append("-u")
        if kwargs.get("quiet"):
            cmd.append("-s")
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

        while revisions:
            self._execVcs(*fetchcmd + ["-r%d"%revisions.pop(0)], **kwargs)
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

    def push(self, *args, **kwargs):
        cmd = ["push"] + list(args)
        status, output = self._execVcs(*cmd, **kwargs)
        return status, output

class GITLook(VCSLook):
    def __init__(self, repospath, txn=None, rev=None):
        VCSLook.__init__(self, repospath, txn, rev)

# vim:et:ts=4:sw=4
