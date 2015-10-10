#!/usr/bin/python3
from MgaRepo.util import execcmd

class SRPM:
    def __init__(self, filename):
        self.filename = filename
        self._getinfo()

    def _getinfo(self):
        cmdstr = "rpm -qp --nosignature --qf '%%{name} %%{epoch} %%{release} %%{version}' %s"
        status, output = execcmd(cmdstr % self.filename)
        self.name, self.epoch, self.release, self.version = output.split()
        if self.epoch == "(none)":
            self.epoch = None

    def unpack(self, topdir):
        execcmd(("rpm -i --nodeps --define '_sourcedir %s/SOURCES' " + 
        "--define '_specdir %s/SPECS' --define '_patchdir %s/SOURCES' %s")
        % (topdir, topdir, topdir, self.filename))

# vim:et:ts=4:sw=4
