#!/usr/bin/python3

from MgaRepo import Error, config

import subprocess
import getpass
import sys
import os
import re
import select
from io import BytesIO
import httplib2
#import commands

# Our own version of commands' commands_exec(). We have a commands
# module directory, so we can't import Python's standard module

def commands_exec(cmdstr, **kwargs):
    err = BytesIO()
    out = BytesIO()
    pstdin = kwargs.get("stdin") if kwargs.get("stdin") else None
    p = subprocess.Popen(cmdstr, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=pstdin)
    of = p.stdout.fileno()
    ef = p.stderr.fileno()
    while True:
        r,w,x = select.select((of,ef), (), ())
        odata = None
        if of in r:
            odata = os.read(of, 8192)
            out.write(odata)
        edata = None
        if ef in r:
            edata = os.read(ef, 8192)
            err.write(edata)
            sys.stderr.buffer.write(edata)
        status = p.poll()
        if status is not None and odata == b'' and edata == b'':
            break
    e = err.getvalue().decode('utf8')
    o = out.getvalue().decode('utf8')
    return o, e, status
    
def execcmd(*cmd, **kwargs):
    cmdstr = " ".join(cmd)
    if kwargs.get('info'):
        prefix='LANGUAGE=C LC_TIME=C '
    else:
        prefix='LANG=C LANGUAGE=C LC_ALL=C '
    if kwargs.get("show"):
        if kwargs.get("geterr"):
            o, output, status = commands_exec(prefix + cmdstr)
        else:
            status = os.system(prefix + cmdstr)
            output = ""
    else:
        output, e, status = commands_exec(prefix + cmdstr)
    verbose = config.getbool("global", "verbose", 0)
    if status != 0 and not kwargs.get("noerror"):
        if kwargs.get("cleanerr") and not verbose:
            raise Error(output)
        else:
            raise Error("command failed: %s\n%s\n" % (cmdstr, output))
    if verbose:
        print(output)
        sys.stdout.buffer.write(output)
    return status, output

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
