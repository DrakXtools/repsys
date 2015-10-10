#!/usr/bin/python
from MgaRepo import Error, config
from MgaRepo.svn import SVN
from MgaRepo.ConfigParser import NoSectionError
import time
import re

class CgiError(Error): pass

class SubmitTarget:
    def __init__(self):
        self.name = ""
        self.target = ""
        self.macros = []
        self.allowed = []
        self.scripts = []

TARGETS = []

def parse_macrosref(refs, config):
    macros = []
    for name in refs:
        secname = "macros %s" % name
        try:
            macros.extend(config.walk(secname, raw=True))
        except NoSectionError:
            raise Error("missing macros section " \
                    "%r in configuration" % secname)
    return macros

def get_targets():
    global TARGETS
    if not TARGETS:
        target = SubmitTarget()
        targetoptions = {}
        submit_re = re.compile("^submit\s+(.+)$")
        for section in config.sections():
            m = submit_re.match(section)
            if m:
                target = SubmitTarget()
                target.name = m.group(1)
                for option, value in config.walk(section):
                    if option in ("target", "allowed", "scripts"):
                        setattr(target, option, value.split())
                    elif option == "rpm-macros":
                        refs = value.split()
                        target.macros = parse_macrosref(refs, config)
                    else:
                        raise Error("unknown [%s] option %s" % (section, option))
                TARGETS.append(target)
    return TARGETS

# vim:et:ts=4:sw=4
