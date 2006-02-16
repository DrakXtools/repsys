from RepSys import Error, config, pexpect
from RepSys.util import execcmd, get_auth
import sys
import re
import time

__all__ = ["SVN", "SVNLook", "SVNLogEntry"]

class SVNLogEntry:
    def __init__(self, revision, author, date):
        self.revision = revision
        self.author = author
        self.date = date
        self.lines = []

    def __cmp__(self, other):
        return cmp(self.date, other.date)

class SVN:
    def __init__(self, username=None, password=None, noauth=0, baseurl=None):
        self.noauth = noauth or (
            baseurl and (
                baseurl.startswith("file:") or
                baseurl.startswith("svn+ssh:")))
        if not self.noauth: # argh
            self.username, self.password = get_auth()


    def _execsvn(self, *args, **kwargs):
        cmdstr = "svn "+" ".join(args)
        if kwargs.get("local") or kwargs.get("noauth") or self.noauth:
            return execcmd(cmdstr, **kwargs)
        show = kwargs.get("show")
        noerror = kwargs.get("noerror")
        p = pexpect.spawn(cmdstr, timeout=1)
        p.setmaxread(1024)
        p.setecho(False)
        outlist = []
        while True:
            i = p.expect_exact([pexpect.EOF, pexpect.TIMEOUT,
                    "username:", "password:",
                    "(p)ermanently?",
                    "Authorization failed"])
            if i == 0:
                if show and p.before:
                    print p.before,
                outlist.append(p.before)
                break
            elif i == 1:
                if show and p.before:
                    print p.before,
                outlist.append(p.before)
            elif i == 2:
                p.sendline(self.username)
                outlist = []
            elif i == 3:
                p.sendline(self.password)
                outlist = []
            elif i == 4:
                p.sendline("p")
                outlist = []
            elif i == 5:
                if not noerror:
                    raise Error, "authorization failed"
                else:
                    break
        while p.isalive():
            try:
                time.sleep(1)
            except (pexpect.TIMEOUT, pexpect.EOF):
                # Continue until the child dies
                pass
        status, output = p.exitstatus, "".join(outlist).strip()
        if status != 0 and not kwargs.get("noerror"):
            sys.stderr.write(cmdstr)
            sys.stderr.write("\n")
            sys.stderr.write(output)
            sys.stderr.write("\n")
            raise Error, "command failed: "+cmdstr
        return status, output

    def _execsvn_success(self, *args, **kwargs):
        status, output = self._execsvn(*args, **kwargs)
        return status == 0

    def _add_log(self, cmd_args, received_kwargs, optional=0):
        if (not optional or
            received_kwargs.has_key("log") or
            received_kwargs.has_key("logfile")):
            ret = received_kwargs.get("log")
            if ret is not None:
                cmd_args.append("-m '%s'" % ret)
            ret = received_kwargs.get("logfile")
            if ret is not None:
                cmd_args.append("-F '%s'" % ret)

    def _add_revision(self, cmd_args, received_kwargs, optional=0):
        if not optional or received_kwargs.has_key("rev"):
            ret = received_kwargs.get("rev")
            if isinstance(ret, basestring):
                try:
                    ret = int(ret)
                except ValueError:
                    raise Error, "invalid revision provided"
            if ret:
                cmd_args.append("-r %d" % ret)
        
    def add(self, path, **kwargs):
        cmd = ["add", path]
        return self._execsvn_success(noauth=1, *cmd, **kwargs)

    def copy(self, pathfrom, pathto, **kwargs):
        cmd = ["copy", pathfrom, pathto]
        self._add_revision(cmd, kwargs, optional=1)
        self._add_log(cmd, kwargs)
        return self._execsvn_success(*cmd, **kwargs)

    def remove(self, path, force=0, **kwargs):
        cmd = ["remove", path]
        self._add_log(cmd, kwargs)
        if force:
            cmd.append("--force")
        return self._execsvn_success(*cmd, **kwargs)

    def mkdir(self, path, **kwargs):
        cmd = ["mkdir", path]
        self._add_log(cmd, kwargs)
        return self._execsvn_success(*cmd, **kwargs)

    def commit(self, path, **kwargs):
        cmd = ["commit", path]
        self._add_log(cmd, kwargs)
        return self._execsvn_success(*cmd, **kwargs)

    def export(self, url, targetpath, **kwargs):
        cmd = ["export", "'%s'" % url, targetpath]
        self._add_revision(cmd, kwargs, optional=1)
        return self._execsvn_success(*cmd, **kwargs)

    def checkout(self, url, targetpath, **kwargs):
        cmd = ["checkout", "'%s'" % url, targetpath]
        self._add_revision(cmd, kwargs, optional=1)
        return self._execsvn_success(*cmd, **kwargs)
 
    def propset(self, propname, value, targets, **kwargs):
        cmd = ["propset", propname, "'%s'" % value, targets]
        return self._execsvn_success(*cmd, **kwargs)

    def propedit(self, propname, target, **kwargs):
        cmd = ["propedit", propname, target]
        if kwargs.get("rev"):
            cmd.append("--revprop")
            self._add_revision(cmd, kwargs)
        return self._execsvn_success(local=True, show=True, *cmd, **kwargs)

    def revision(self, path, **kwargs):
        cmd = ["info", path]
        status, output = self._execsvn(local=True, *cmd, **kwargs)
        if status == 0:
            for line in output.splitlines():
                if line.startswith("Revision: "):
                    return int(line.split()[1])
        return None
          
    def info(self, path, **kwargs):
        cmd = ["info", path]
        status, output = self._execsvn(local=True, *cmd, **kwargs)
        if status == 0:
            return output.splitlines()
        return None
          
    def ls(self, path, **kwargs):
        cmd = ["ls", path]
        status, output = self._execsvn(*cmd, **kwargs)
        if status == 0:
            return output.split()
        return None

    def status(self, path, **kwargs):
        cmd = ["status", path]
        if kwargs.get("verbose"):
            cmd.append("-v")
        status, output = self._execsvn(*cmd, **kwargs)
        if status == 0:
            return [x.split() for x in output.splitlines()]
        return None

    def cleanup(self, path, **kwargs):
        cmd = ["cleanup", path]
        return self._execsvn_success(*cmd, **kwargs)

    def revert(self, path, **kwargs):
        cmd = ["revert", path]
        status, output = self._execsvn(*cmd, **kwargs)
        if status == 0:
            return [x.split() for x in output.split()]
        return None

    def update(self, path, **kwargs):
        cmd = ["update", path]
        self._add_revision(cmd, kwargs, optional=1)
        status, output = self._execsvn(*cmd, **kwargs)
        if status == 0:
            return [x.split() for x in output.split()]
        return None

    def merge(self, url1, url2=None, rev1=None, rev2=None, path=None, **kwargs):
        cmd = ["merge"]
        if rev1 and rev2 and not url2:
            cmd.append("-r")
            cmd.append("%s:%s" % (rev1, rev2))
            cmd.append(url1)
        else:
            if not url2:
                raise ValueError, \
                      "url2 needed if two revisions are not provided"
            if rev1:
                cmd.append("%s@%s" % (url1, rev1))
            else:
                cmd.append(url1)
            if rev2:
                cmd.append("%s@%s" % (url2, rev2))
            else:
                cmd.append(url2)
        if path:
            cmd.append(path)
        status, output = self._execsvn(*cmd, **kwargs)
        if status == 0:
            return [x.split() for x in output.split()]
        return None

    def diff(self, pathurl1, pathurl2=None, **kwargs):
        cmd = ["diff", pathurl1]
        self._add_revision(cmd, kwargs, optional=1)
        if pathurl2:
            cmd.append(pathurl2)
        status, output = self._execsvn(*cmd, **kwargs)
        if status == 0:
            return output
        return None

    def cat(self, url, **kwargs):
        cmd = ["cat", url]
        self._add_revision(cmd, kwargs, optional=1)
        status, output = self._execsvn(*cmd, **kwargs)
        if status == 0:
            return output
        return None

    def log(self, url, start=None, end=0, limit=None, **kwargs):
        cmd = ["log", url]
        if start is not None or end != 0:
            if start is not None and type(start) is not type(0):
                try:
                    start = int(start)
                except (ValueError, TypeError):
                    raise Error, "invalid log start revision provided"
            if type(end) is not type(0):
                try:
                    end = int(end)
                except (ValueError, TypeError):
                    raise Error, "invalid log end revision provided"
            start = start or "HEAD"
            cmd.append("-r %s:%s" % (start, end))
        if limit is not None:
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                raise Error, "invalid limit number provided"
            cmd.append("--limit %d" % limit)
        status, output = self._execsvn(*cmd, **kwargs)
        if status != 0:
            return None

        revheader = re.compile("^r(?P<revision>[0-9]+) \| (?P<author>[^\|]+) \| (?P<date>[^\|]+) \| (?P<lines>[0-9]+) (?:line|lines)$")
        logseparator = "-"*72
        linesleft = 0
        entry = None
        log = []
        emptyline = 0
        for line in output.splitlines():
            if emptyline:
                emptyline = 0
                continue
            line = line.rstrip()
            if linesleft == 0:
                if line != logseparator:
                    m = revheader.match(line)
                    if m:
                        linesleft = int(m.group("lines"))
                        timestr = " ".join(m.group("date").split()[:2])
                        timetuple = time.strptime(timestr,
                                                  "%Y-%m-%d %H:%M:%S")
                        entry = SVNLogEntry(int(m.group("revision")),
                                            m.group("author"), timetuple)
                        log.append(entry)
                        emptyline = 1
            else:
                entry.lines.append(line)
                linesleft -= 1
        log.sort()
        log.reverse()
        return log

class SVNLook:
    def __init__(self, repospath, txn=None, rev=None):
        self.repospath = repospath
        self.txn = txn
        self.rev = rev

    def _execsvnlook(self, cmd, *args, **kwargs):
        execcmd_args = ["svnlook", cmd, self.repospath]
        self._add_txnrev(execcmd_args, kwargs)
        execcmd_args += args
        execcmd_kwargs = {}
        keywords = ["show", "noerror"]
        for key in keywords:
            if kwargs.has_key(key):
                execcmd_kwargs[key] = kwargs[key]
        return execcmd(*execcmd_args, **execcmd_kwargs)

    def _add_txnrev(self, cmd_args, received_kwargs):
        if received_kwargs.has_key("txn"):
            txn = received_kwargs.get("txn")
            if txn is not None:
                cmd_args += ["-t", txn]
        elif self.txn is not None:
            cmd_args += ["-t", self.txn]
        if received_kwargs.has_key("rev"):
            rev = received_kwargs.get("rev")
            if rev is not None:
                cmd_args += ["-r", rev]
        elif self.rev is not None:
            cmd_args += ["-r", self.rev]

    def changed(self, **kwargs):
        status, output = self._execsvnlook("changed", **kwargs)
        if status != 0:
            return None
        changes = []
        for line in output.splitlines():
            line = line.rstrip()
            if not line:
                continue
            entry = [None, None, None]
            changedata, changeprop, path = None, None, None
            if line[0] != "_":
                changedata = line[0]
            if line[1] != " ":
                changeprop = line[1]
            path = line[4:]
            changes.append((changedata, changeprop, path))
        return changes

    def author(self, **kwargs):
        status, output = self._execsvnlook("author", **kwargs)
        if status != 0:
            return None
        return output.strip()

# vim:et:ts=4:sw=4
