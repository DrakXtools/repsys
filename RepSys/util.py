#!/usr/bin/python
from RepSys import Error, config
import getpass
import sys, os
#import commands

# Our own version of commands' getstatusoutput(). We have a commands
# module directory, so we can't import Python's standard module
def commands_getstatusoutput(cmd):
    """Return (status, output) of executing cmd in a shell."""
    import os
    pipe = os.popen('{ ' + cmd + '; } 2>&1', 'r')
    text = pipe.read()
    sts = pipe.close()
    if sts is None: sts = 0
    if text[-1:] == '\n': text = text[:-1]
    return sts, text

def execcmd(*cmd, **kwargs):
    cmdstr = " ".join(cmd)
    if kwargs.get("show"):
        status = os.system(cmdstr)
        output = ""
    else:
        status, output = commands_getstatusoutput("LANG=C LANGUAGE=C LC_ALL=C "+cmdstr)
    if status != 0 and not kwargs.get("noerror"):
        raise Error, "command failed: %s\n%s\n" % (cmdstr, output)
    if config.getbool("global", "verbose", 0):
        print cmdstr
        sys.stdout.write(output)
    return status, output

def get_auth(username=None, password=None):
    set_username = 1
    set_password = 1
    if not username:
        username = config.get("auth", "username")
        if not username:
            username = raw_input("username: ")
        else:
            set_username = 0
    if not password:
        password = config.get("auth", "password")
        if not password:
            password = getpass.getpass("password: ")
        else:
            set_password = 0
    if set_username:
        config.set("auth", "username", username)
    if set_password:
        config.set("auth", "password", password)
    return username, password

# vim:et:ts=4:sw=4
