from RepSys import Error, config
from RepSys.util import execcmd
from RepSys.VCS import VCS
from RepSys.git import GIT
from RepSys.log import UserTagParser
from os.path import basename, dirname, abspath, lexists, join
from os import chdir, environ, getcwd
from tempfile import mkstemp
import sys
import re
import time
import progressbar
from xml.etree import ElementTree
import subprocess

class GITSVN(GIT):
    vcs_dirname = ".git/svn"
    vcs_name = "git"
    def __init__(self, path=None, url=None):
        GIT.__init__(self, path, url)
        vcs = getattr(VCS, "vcs")
        vcs.append((self.vcs_name, self.vcs_dirname))
        setattr(VCS,"vcs", vcs)
        self.vcs_command = config.get("global", "git-command", ["git"])
        self.vcs_supports['clone'] = True
        self.env_defaults = {"GIT_SSH": self.vcs_wrapper}

    def clone(self, url=None, targetpath=None, fullnames=True, **kwargs):
        if not VCS.clone(self, url, targetpath, **kwargs):
            self.init(url, targetpath, fullnames=True, **kwargs)
            return self.update(targetpath, clone=True, **kwargs)

    def verifyrepo(self):
        return True

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
        environ.update({"GIT_WORK_TREE" : abspath(targetpath), "GIT_DIR" : join(abspath(targetpath),".git")})

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
        environ.update({"GIT_WORK_TREE" : abspath(targetpath), "GIT_DIR" : join(abspath(targetpath),".git")})

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

            # we're already at latest revision
            if revision[0][1:] == lastrev:
                print("At revision %s." % lastrev)
                return None

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
        commits = len(revisions)

        fetchcmd = ["svn", "fetch", "--log-window-size=1000"]
        gitconfig = self.configget("svn-remote.authorlog")
        if gitconfig:
            usermap = UserTagParser(url=gitconfig.get("svn-remote.authorlog.url"),defaultmail=gitconfig.get("svn-remote.authorlog.defaultmail"))
            usermapfile = usermap.get_user_map_file()
            fetchcmd.extend(("--authors-file", usermapfile))
        fetchcmd.append("")

        commit = 0
        bar = progressbar.ProgressBar(max_value=commits,redirect_stdout=True)
        print("Fetching %d revisions in the range %d - %d" % (commits, revisions[0], revisions[-1]))
        while revisions:
            rev = revisions.pop(0)
            print("Fetching revision %d" % rev)
            fetchcmd[-1] = "-r%d"%rev
            self._execVcs(*fetchcmd, **kwargs)
            commit += 1
            bar.update(commit)
        if gitconfig:
            usermap.cleanup()
        bar.finish()

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

    def drop_ssh_if_no_auth(self, url):
        if url and url.startswith("svn+ssh://"):
            cmd = ["svn", "info", "--non-interactive", "--no-newline", "--show-item", "url", url]
            status, output = self._execVcs(*cmd, local=True, noerror=True, show=False)
            if status == 1 and (("E170013" in output) or ("E210002" in output)):
                url = url.replace("svn+ssh://", "svn://")
                status, output = execcmd(*cmd, local=True, noerror=True, show=False)
                if status == 0 and output == url:
                    pass
        return url

    @property
    def url(self):
        if not self._url:
            self._url = self.drop_ssh_if_no_auth(self._URL or self.info2(self._path)["URL"])
        return self._url

# vim:et:ts=4:sw=4
