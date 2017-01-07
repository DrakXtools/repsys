from RepSys import Error, config
from RepSys.rpmutil import get_pkg_tag, clone
from RepSys.util import execcmd
from RepSys.git import GIT
import os

class GitFedora(object):
    def __init__(self, package):
        self._package = package
        self._login = config.get("fedora", "login")
        if self._login:
            self._repourl = "ssh://"+self._login+"@pkgs.fedoraproject.org/rpms/"+package
        else:
            self._repourl = "https://src.fedoraproject.org/git/rpms/"+package+GIT.vcs_dirname

    def clone_repository(self, pkgname, target=None):
        print(self._repourl)
        git = GIT(path=target, url=self._repourl);
        git.clone()

        return True
        #raise Error("Repository %s doesn't exist!" % repository)
