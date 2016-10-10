from MgaRepo.util import execcmd

class SRPM:
    def __init__(self, filename):
        self.filename = filename
        self._getinfo()

    def _getinfo(self):
        args = ["rpm", "-qp", "--qf", "%{name} %{epoch} %{release} %{version}",
                self.filename]
        status, output = execcmd(args)
        self.name, self.epoch, self.release, self.version = output.split()
        if self.epoch == "(none)":
            self.epoch = None

    def unpack(self, topdir):
        args = ["rpm", "-i", "--nodeps", 
              "--define", "'_sourcedir "+topdir+"/SOURCES'",
              "--define", "'_specdir " + topdir + "/SPECS'", 
              "--define", "'_patchdir " + topdir+"/SOURCES'", 
              self.filename]
        execcmd(args)

# vim:et:ts=4:sw=4
