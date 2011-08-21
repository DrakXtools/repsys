from MgaRepo import Error, config, mirror, layout
from MgaRepo.util import execcmd, rellink, get_helper
from MgaRepo.svn import SVN

import sys
import os
import string
import stat
import shutil
import re
import tempfile
import hashlib
import urlparse
import threading
import httplib2
from cStringIO import StringIO

SOURCES_FILE = "sha1.lst"

class ChecksumError(Error):
    pass

def is_binary(path):
    raw = config.get("binrepo", "upload-match",
            "\.(7z|Z|bin|bz2|cpio|db|deb|egg|gem|gz|jar|jisp|lzma|"\
               "pdf|pgn\\.gz|pk3|png|rpm|run|sdz|smzip|tar|tbz|"\
               "tbz2|tgz|ttf|uqm|wad|war|xar|xpi|xz|zip|wav|mp3|ogg|"\
	       "jpg|png|gif|avi|mpg|mpeg|rar)$")
    maxsize = config.getint("binrepo", "upload-match-size", "1048576") # 1MiB
    expr = re.compile(raw)
    name = os.path.basename(path)
    if expr.search(name):
        return True
    st = os.stat(path)
    if st[stat.ST_SIZE] >= maxsize:
        return True
    return False

def find_binaries(paths):
    new = []
    for path in paths:
        if os.path.isdir(path):
            for name in os.listdir(path):
                fpath = os.path.join(path, name)
                if is_binary(fpath):
                    new.append(fpath)
        else:
            if is_binary(path):
                new.append(path)
    return new

def download_binary(topdir, sha1, filename):
    fmt = config.get("global", "download-command",
	    "wget -c -O '$dest' $url")
    url = config.get("binrepo", "download_url",
	    "http://binrepo.mageia.org/")
    url = mirror.normalize_path(url + "/" + sha1)
    dest = os.path.join(topdir, 'SOURCES', filename)
    if os.path.exists(dest):
	if file_hash(dest) == sha1:
	    return 1
	else:
	    raise Error, "File with incorrect sha1sum: %s" % dest
    context = {"dest": dest, "url": url}
    try:
	cmd = string.Template(fmt).substitute(context)
    except KeyError, e:
	raise Error, "invalid variable %r in download-command "\
		"configuration option" % e
    try:
	status, output = execcmd(cmd, show=True)
    except Error, e:
	os.unlink(dest)
	raise Error, "Could not download file %s\n" % url

def download_binaries(topdir):
    spath = sources_path(topdir)
    if not os.path.exists(spath):
        raise Error, "'%s' was not found" % spath
    entries = parse_sources(spath)
    for name, sha1 in entries.iteritems():
	download_binary(topdir, sha1, name)

def binary_exists(sha1sum):
    dlurl = config.get("binrepo", "download_url",
	    "http://binrepo.mageia.org/")
    dlurl = mirror.normalize_path(dlurl + "/" + sha1sum)
    h = httplib2.Http()
    resp, content = h.request(dlurl, 'HEAD')
    return resp.status == 200

def upload_binary(topdir, filename):
    filepath = os.path.join(topdir, 'SOURCES', filename)
    if not os.path.exists(filepath):
        raise Error, "'%s' was not found" % spath
    sha1sum = file_hash(filepath)
    if binary_exists(sha1sum):
	return
    host = config.get("binrepo", "upload_host")
    upload_bin_helper = get_helper("upload-bin")
    command = "ssh %s %s %s" % (host, upload_bin_helper, filename)
    try:
	filein = open(filepath, 'r')
    except Error, e:
	raise Error, "Could not open file %s\n" % filepath
    status, output = execcmd(command, show=True, geterr=True, stdin=filein)

def import_binaries(topdir, pkgname):
    """Import all binaries from a given package checkout

    @topdir: the path to the svn checkout
    """
    sourcesdir = os.path.join(topdir, "SOURCES")
    binaries = find_binaries([sourcesdir])
    for path in binaries:
	upload_binary(topdir, os.path.basename(path))
    update_sources(topdir, added=binaries)
    svn = SVN()
    svn.add(sources_path(topdir))

def parse_sources(path):
    entries = {}
    f = open(path)
    for rawline in f:
        line = rawline.strip()
        try:
            sum, name = line.split(None, 1)
        except ValueError:
            # failed to unpack, line format error
            raise Error, "invalid line in sources file: %s" % rawline
        entries[name] = sum
    return entries

def file_hash(path):
    sum = hashlib.sha1()
    f = open(path)
    while True:
        block = f.read(4096)
        if not block:
            break
        sum.update(block)
    f.close()
    return sum.hexdigest()

def sources_path(topdir):
    path = os.path.join(topdir, "SOURCES", SOURCES_FILE)
    return path

def update_sources(topdir, added=[], removed=[]):
    path = sources_path(topdir)
    entries = {}
    if os.path.isfile(path):
        entries = parse_sources(path)
    f = open(path, "w") # open before calculating hashes
    for name in removed:
	if name in entries:
           del entries[name]
    for added_path in added:
        name = os.path.basename(added_path)
        entries[name] = file_hash(added_path)
    for name in sorted(entries):
        f.write("%s  %s\n" % (entries[name], name))
    f.close()

