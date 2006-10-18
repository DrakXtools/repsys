#!/usr/bin/python
from RepSys import Error, config
from RepSys.svn import SVN
import time
import re

class CgiError(Error): pass

class SubmitTarget:
    def __init__(self):
        self.name = ""
        self.target = ""
        self.allowed = []
        self.scripts = []

TARGETS = []

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
                    if option == "target":
                        target.target = value.split()
                    elif option == "allowed":
                        target.allowed = value.split()
                    elif option == "scripts":
                        target.scripts = value.split()
                    else:
                        raise Error, "unknown [%s] option %s" % (section, option)
                TARGETS.append(target)
    return TARGETS

# vim:et:ts=4:sw=4
