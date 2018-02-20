from RepSys import Error, config
from RepSys.rpmutil import get_pkg_tag, clone
from RepSys.util import execcmd
from RepSys.git import GIT
from os.path import join
import yaml

class GitABF(object):
    binrepo = "http://file-store.openmandriva.org/download/"
    def __init__(self, package):
        self._package = package
        self._project = config.get("abf", "project", "OpenMandrivaAssociation")
        self._protocol = config.get("abf", "protocol", "https")
        self._login = config.get("abf", "login")
        self._password = config.get("abf", "password")
        if self._protocol == "ssh":
            self._repourl = "ssh://git@github.com/"+self._project+"/"+self._package+".git"
        else:
            auth = ""
            if self._login:
                auth += self._login
                if self._password:
                    auth += ":"+self._password
                auth += "@"
            self._repourl = "https://"+auth+"github.com/"+self._project+"/"+self._package+".git"
        self._git = GIT(url=self._repourl)

    def clone_repository(self):
        self._git.clone()
        self.download_sources()

        return True

    def download_sources(self):
        f = open(join(self._git.path, ".abf.yml"))
        y = yaml.load(f.read())
        f.close()
        downloader = config.get("global", "download-command",
                "wget -c -O '$dest' $url").strip("'$dest' $url").split()
        for source in y["sources"].items():
            self.download_source(downloader, source[0], source[1])

    def download_source(self, downloader, filename, checksum):
        binurl = self.binrepo+"/"+checksum
        cmd = downloader + [join(self._git.path, filename), binurl]

        status, output = execcmd(cmd, show=True)
        if status == 0:
            return True
        else:
            raise Error("Failed downloading %s, retcode: %d err: %s\n", status, output)
