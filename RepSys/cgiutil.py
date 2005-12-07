#!/usr/bin/python
from RepSys import Error, config
from RepSys.svn import SVN
import time

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
        for option, value in config.walk("submit"):
            if targetoptions.has_key(option):
                TARGETS.append(target)
                target = SubmitTarget()
                targetoptions = {}
            targetoptions[option] = 1
            if option == "name":
                target.name = value
            elif option == "target":
                target.target = value.split()
            elif option == "allowed":
                target.allowed = value.split()
            elif option == "scripts":
                target.scripts = value.split()
            else:
                raise Error, "unknown [submit] option %s" % option
        if targetoptions:
            TARGETS.append(target)
    return TARGETS

# vim:et:ts=4:sw=4
