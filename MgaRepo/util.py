#!/usr/bin/python3

from MgaRepo import Error, config

import shlex
import subprocess
import getpass
import sys
import os
import re
import select
from io import StringIO
import httplib2

class CommandError(Error):
    def __init__(self, cmdline, status, output):
        self.cmdline = cmdline
        self.status = status
        self.output = output

    def __str__(self):
        return "command failed: %s\n%s\n" % (self.cmdline, self.output)

def execcmd(*cmd, **kwargs):
    assert (kwargs.get("collecterr") and kwargs.get("show")) or not kwargs.get("collecterr"), \
            ("execcmd is implemented to handle collecterr=True only if show=True")
    # split command args
    if isinstance(cmd[0], str):
        cmdargs = shlex.split(cmd[0])
    else:
        cmdargs = cmd[0][:]

    stdout = None
    stderr = None
    env = {}
    env.update(os.environ)
    if kwargs.get("info") or not kwargs.get("show") or (kwargs.get("show") and kwargs.get("collecterr")):
        if kwargs.get("info"):
            env.update({"LANGUAGE": "C", "LC_TIME": "C"})
        else:
            env.update({"LANG": "C", "LANGUAGE": "C", "LC_ALL": "C"})
        stdout = subprocess.PIPE
        if kwargs.get("collecterr"):
            stderr = subprocess.PIPE
        else:
            stderr = subprocess.STDOUT

    proc = subprocess.Popen(cmdargs, shell=False, stdout=stdout,
            stderr=stderr, env=env)

    output = ""

    if kwargs.get("show") and kwargs.get("collecterr"):
        error = StringIO()
        wl = []
        outfd = proc.stdout.fileno()
        errfd = proc.stderr.fileno()
        rl = [outfd, errfd]
        xl = wl
        while proc.poll() is None:
            mrl, _, _ = select.select(rl, wl, xl, 0.5)
            for fd in mrl:
                data = os.read(fd, 8192).decode('utf8')
                if fd == errfd:
                    error.write(data)
                    sys.stderr.write(data)
                else:
                    sys.stdout.write(data)
        output = error.getvalue()
    else:
        proc.wait()
        if proc.stdout is not None:
            output = proc.stdout.read().decode('utf8')
            if kwargs.get("strip", True):
                output = output.rstrip()

    if (not kwargs.get("noerror")) and proc.returncode != 0:
        if kwargs.get("cleanerr"):
            msg = output
        cmdline = subprocess.list2cmdline(cmdargs)
        raise CommandError(cmdline, proc.returncode, output)

    return proc.returncode, output

def get_output_exec(cmdstr):
    output = StringIO()
    err = StringIO()
    p = subprocess.Popen(cmdstr, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    of = p.stdout.fileno()
    ef = p.stderr.fileno()
    while True:
        r,w,x = select.select((of,ef), (), ())
        odata = None
        if of in r:
            odata = (os.read(of, 8192)).decode('utf8')
            output.write(odata)
        edata = None
        if ef in r:
            edata = (os.read(ef, 8192)).decode('utf8')
            err.write(edata)
        status = p.poll()
        if status is not None and odata == '' and edata == '':
            break
    return output.getvalue()

def get_auth(username=None, password=None):
    set_username = 1
    set_password = 1
    if not username:
        username = config.get("auth", "username")
        if not username:
            username = input("username: ")
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


def mapurl(url):
    """Maps a url following the regexp provided by the option url-map in
    mgarepo.conf
    """
    urlmap = config.get("global", "url-map")
    newurl = url
    if urlmap:
        try:
            expr_, replace = urlmap.split()[:2]
        except ValueError:
            sys.stderr.buffer.write("invalid url-map: %s" % urlmap)
        else:
            try:
                newurl = re.sub(expr_, replace, url)
            except re.error as errmsg:
                sys.stderr.buffer.write("error in URL mapping regexp: %s" % errmsg)
    return newurl


def get_helper(name):
    """Tries to find the path of a helper script

    It first looks if the helper has been explicitly defined in
    configuration, if not, falls back to the default helper path, which can
    also be defined in configuration file(s).
    """
    helperdir = config.get("helper", "prefix", "/usr/share/mgarepo")
    hpath = config.get("helper", name, None) or \
            os.path.join(helperdir, name)
    return hpath

def rellink(src, dst):
    """Creates relative symlinks

    It will find the common ancestor and append to the src path.
    """
    asrc = os.path.abspath(src)
    adst = os.path.abspath(dst)
    csrc = asrc.split(os.path.sep)
    cdst = adst.split(os.path.sep)
    dstname = cdst.pop()
    i = 0
    l = min(len(csrc), len(cdst))
    while i < l:
        if csrc[i] != cdst[i]:
            break
        i += 1
    dstextra = len(cdst[i:])
    steps = [os.path.pardir] * dstextra
    steps.extend(csrc[i:])
    return os.path.sep.join(steps)
    
def maintdb_get(package):
    dlurl = config.get("maintdb", "url",
            "http://maintdb.mageia.org/")
    dlurl = dlurl + "/" + package
    h = httplib2.Http()
    resp, content = h.request(dlurl, 'GET')
    if resp.status != 200:
        raise Exception('Package cannot be found in maintdb')
    return content.rstrip('\n')

# vim:et:ts=4:sw=4
