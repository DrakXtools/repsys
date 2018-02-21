from RepSys import Error
from RepSys.git import GIT
from RepSys.gitsvn import GITSVN
from RepSys.svn import SVN
from RepSys.osc import OSC
import os

def detectVCS(url):
    if '://' in url:
        protocol,uri = url.split("://")
        if "svn" in protocol:
            return SVN(url=url)
        elif "git" in protocol:
            return GIT(url=url)
        elif "http" in protocol:
            if uri.endswith(".git"):
                return GIT(url=url)
            elif "svn" in uri:
                return SVN(url=url)
        raise Error("Unknown protocol %s for %s" % (protocol, url))
    elif os.path.exists(url) and os.path.isdir(url):
        while True:
            url = os.path.abspath(url)
            for vcs in (SVN, GITSVN, GIT, OSC):
                vcsdir = os.path.join(url, vcs.vcs_dirname)
                if os.path.exists(vcsdir) and os.path.isdir(vcsdir):
                    return vcs(path=url)
            url = os.path.dirname(url)
            if url == "/":
                break
    raise Error("No supported repository found at path: %s" % url)
