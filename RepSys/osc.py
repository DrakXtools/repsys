from RepSys.VCS import *

class OSCLogEntry(VCSLogEntry):
    def __init__(self, revision, author, date):
        VCSLogEntry.__init__(self, revision, author, data)

class OSC(VCS):
    vcs_dirname = ".osc"
    vcs_name = "osc"
    def __init__(self, path=None, url=None):
        VCS.__init__(self, path, url)
        vcs = getattr(VCS, "vcs")
        vcs.append((self.vcs_name, self.vcs_dirname))
        setattr(VCS,"vcs", vcs)

class OSCLook(VCSLook):
    def __init__(self, repospath, txn=None, rev=None):
        VCSLook.__init__(self, repospath, txn, rev)

# vim:et:ts=4:sw=4
