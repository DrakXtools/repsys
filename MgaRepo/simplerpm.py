#!/usr/bin/python
from MgaRepo.util import execcmd

class SRPM:
    def __init__(self, filename):
        self.filename = filename
        self._getinfo()

    def _getinfo(self):
        cmdstr = "rpm -qp --qf '%%{name} %%{epoch} %%{release} %%{version}' %s"
        status, output = execcmd(cmdstr % self.filename)
        self.name, self.epoch, self.release, self.version = output.split()
        if self.epoch == "(none)":
            self.epoch = None

    def unpack(self, topdir):
        execcmd("rpm -i --define '_topdir %s' %s" % (topdir, self.filename))

# vim:et:ts=4:sw=4
