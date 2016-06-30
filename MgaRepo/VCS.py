from MgaRepo import Error, SilentError, config
from MgaRepo.util import execcmd, get_auth
from MgaRepo import layout
from xml.etree import ElementTree
import sys
import os
import re
import time

class VCSLogEntry(object):
    def __init__(self, revision, author, date, lines=[], changed=[]):
        self.revision = revision
        self.author = author
        self.date = date
        self.changed = changed
        self.lines = lines

    def __lt__(self, other):
        return (self.date < other.date)
    
    def __eq__(self,other):
        return (self.date == other.date)

class VCS(object):
    vcs_dirname = None
    vcs_name = None
    def __init__(self, path, url):
        self.vcs_command = None
        self.vcs_wrapper = "mga-ssh"
        self.vcs_supports = {'clone' : False}
        self.vcs_type = None
        self.env_defaults = None
        if not path and not url:
            self._path = os.path.curdir
        elif not path and url:
            self._path = layout.package_name(layout.remove_current(url))
        else:
            self._path = path
        self._url = url

    def _execVcs(self, *args, **kwargs):
        localcmds = ("add", "revert", "cleanup", "mv")
        cmd = self.vcs_command + list(args)
        kwargs["collecterr"] = kwargs.get("collecterr", False)
        if kwargs.get("show"):
            if not kwargs.get("local"):
               kwargs["collecterr"] = True
        else:
            if self.vcs_command is "svn" and args[0] not in localcmds:
                cmd.append("--non-interactive")
            else:
                if args[0] == "mv":
                    kwargs["collecterr"] = False
        kwargs["cleanerr"] = kwargs.get("cleanerr", True)
        if kwargs.get("xml"):
            cmd.append("--xml")
        try:
            if args[0] in ('info', 'checkout','log'):
                kwargs['info'] = True
            else:
                kwargs['info'] = False
            return execcmd(*cmd, **kwargs)
        except Error as e:
            msg = None
            if e.args:
                if "Permission denied" in e.args:
                    msg = ("It seems ssh-agent or ForwardAgent are not setup "
                           "or your username is wrong. See "
                           "https://wiki.mageia.org/en/Packagers_ssh"
                           " for more information.")
                elif "authorization failed" in e.args:
                    msg = ("Note that mgarepo does not support any HTTP "
                           "authenticated access.")
            if kwargs.get("show") and \
                    not config.getbool("global", "verbose", 0):
                # svn has already dumped error messages, we don't need to
                # do it too
                if msg:
                    sys.stderr.write("\n")
                    sys.stderr.write(msg)
                    sys.stderr.write("\n")
                raise SilentError
            elif msg:
                raise Error("%s\n%s" % (e, msg))
            raise

    def _set_env(self):
        wrapper = "mgarepo-ssh"
        repsys = config.get("global", "mgarepo-cmd")
        if repsys:
            dir = os.path.dirname(repsys)
            path = os.path.join(dir, wrapper)
            if os.path.exists(path):
                wrapper = path
        defaults = {"SVN_SSH": wrapper}
        os.environ.update(defaults)
        raw = config.get("global", "svn-env")
        if raw:
            for line in raw.split("\n"):
                env = line.strip()
                if not env:
                    continue
                try:
                    name, value = env.split("=", 1)
                except ValueError:
                    sys.stderr.write("invalid svn environment line: %r\n" % env)
                    continue
                os.environ[name] = value

    def _execVcs_success(self, *args, **kwargs):
        status, output = self._execVcs(*args, **kwargs)
        return status == 0

    def _add_log(self, cmd_args, received_kwargs, optional=0):
        if (not optional or
            "log" in received_kwargs or
            "logfile" in received_kwargs):
            ret = received_kwargs.get("log")
            if ret is not None:
                cmd_args.extend(("-m", ret))
            ret = received_kwargs.get("logfile")
            if ret is not None:
                cmd_args.extend(("-F", ret))

    def _add_revision(self, cmd_args, received_kwargs, optional=0):
        if not optional or "rev" in received_kwargs:
            ret = received_kwargs.get("rev")
            if isinstance(ret, str):
                if not ret.startswith("{"): # if not a datespec
                    try:
                        ret = int(ret)
                    except ValueError:
                        raise Error("invalid revision provided")
            if ret:
                cmd_args.extend(("-r", str(ret)))
        
    def add(self, path, **kwargs):
        cmd = ["add", path + '@' if '@' in path else path]
        return self._execVcs_success(noauth=1, *cmd, **kwargs)

    def copy(self, pathfrom, pathto, **kwargs):
        cmd = ["copy", pathfrom + '@' if '@' in pathfrom else pathfrom, pathto + '@' if '@' in pathto else pathto]
        self._add_revision(cmd, kwargs, optional=1)
        self._add_log(cmd, kwargs)
        return self._execVcs_success(*cmd, **kwargs)

    def remove(self, path, force=0, **kwargs):
        cmd = ["remove", path + '@' if '@' in path else path]
        self._add_log(cmd, kwargs)
        if force:
            cmd.append("--force")
        return self._execVcs_success(*cmd, **kwargs)

    def mkdir(self, path, **kwargs):
        cmd = ["mkdir", path + '@' if '@' in path else path]
        if kwargs.get("parents"):
            cmd.append("--parents")
        self._add_log(cmd, kwargs)
        return self._execVcs_success(*cmd, **kwargs)

    def _execVcs_commit(self, *cmd, **kwargs):
        status, output = self._execVcs(*cmd, **kwargs)
        match = re.search("Committed revision (?P<rev>\\d+)\\.$", output)
        if match:
            rawrev = match.group("rev")
            return int(rawrev)

    def commit(self, path, **kwargs):
        cmd = ["commit", path + '@' if '@' in path else path]
        if kwargs.get("nonrecursive"):
            cmd.append("-N")
        self._add_log(cmd, kwargs)
        return self._execVcs_commit(*cmd, **kwargs)

    def import_(self, path, url, **kwargs):
        cmd = ["import", path, url]
        self._add_log(cmd, kwargs)
        return self._execVcs_commit(*cmd, **kwargs)

    def export(self, url, targetpath, **kwargs):
        cmd = ["export", url, targetpath]
        self._add_revision(cmd, kwargs, optional=1)
        return self._execVcs_success(*cmd, **kwargs)

    def checkout(self, url, targetpath, **kwargs):
        cmd = ["checkout", url, targetpath]
        self._add_revision(cmd, kwargs, optional=1)
        return self._execVcs_success(*cmd, **kwargs)

    def clone(self, url, targetpath, **kwargs):
        if self.vcs_supports['clone']:
            cmd = ["clone", url, targetpath]
            return self._execVcs_success(*cmd, **kwargs)
        else:
            raise Error("%s doesn't support 'clone'" % self.vcs_name)

    def propget(self, propname, targets, **kwargs):
        cmd = ["propget", propname, targets]
        if kwargs.get("revprop"):
            cmd.append("--revprop")
        self._add_revision(cmd, kwargs)
        status, output = self._execVcs(local=True, *cmd, **kwargs)
        return output
 
    def propset(self, propname, value, targets, **kwargs):
        cmd = ["propset", propname, value, targets]
        return self._execVcs_success(*cmd, **kwargs)

    def propedit(self, propname, target, **kwargs):
        cmd = ["propedit", propname, target]
        if kwargs.get("rev"):
            cmd.append("--revprop")
            self._add_revision(cmd, kwargs)
        return self._execVcs_success(local=True, show=True, *cmd, **kwargs)

    def revision(self, path, **kwargs):
        cmd = ["info", path + '@' if '@' in path else path]
        status, output = self._execVcs(local=True, *cmd, **kwargs)
        if status == 0:
            for line in output.splitlines():
                if line.startswith("Last Changed Rev: "):
                    return int(line.split()[3])
        return None
          
    def info(self, path, **kwargs):
        cmd = ["info", path + '@' if '@' in path else path]
        status, output = self._execVcs(local=True, noerror=True, *cmd, **kwargs)
        if (("Not a versioned resource" not in output) and ("svn: warning: W155010" not in output)):
            return output.splitlines()
        return None

    def info2(self, *args, **kwargs):
        lines = self.info(*args, **kwargs)
        if lines is None:
            return None
        pairs = [[w.strip() for w in line.split(":", 1)] for line in lines]
        info = {}
        for pair in pairs:
            if pair != ['']:
                info[pair[0]]=pair[1]
        return info
          
    def ls(self, path, **kwargs):
        cmd = ["ls", path + '@' if '@' in path else path]
        status, output = self._execVcs(*cmd, **kwargs)
        if status == 0:
            return output.split()
        return None

    def status(self, path, **kwargs):
        cmd = ["status", path + '@' if '@' in path else path]
        if kwargs.get("verbose"):
            cmd.append("-v")
        if kwargs.get("noignore"):
            cmd.append("--no-ignore")
        if kwargs.get("quiet"):
            cmd.append("--quiet")
        status, output = self._execVcs(*cmd, **kwargs)
        if status == 0:
            return [(x[0], x[8:]) for x in output.splitlines()]
        return None

    def cleanup(self, path, **kwargs):
        cmd = ["cleanup", path + '@' if '@' in path else path]
        return self._execVcs_success(*cmd, **kwargs)

    def revert(self, path, **kwargs):
        cmd = ["revert", path + '@' if '@' in path else path]
        status, output = self._execVcs(*cmd, **kwargs)
        if status == 0:
            return [x.split() for x in output.split()]
        return None

    def switch(self, url, oldurl=None, path=None, relocate=False, **kwargs):
        cmd = ["switch"]
        if relocate:
            if oldurl is None:
                raise Error("You must supply the old URL when "\
                        "relocating working copies")
            cmd.append("--relocate")
            cmd.append(oldurl)
        cmd.append(url)
        if path is not None:
            cmd.append(path)
        return self._execVcs_success(*cmd, **kwargs)

    def update(self, path, **kwargs):
        cmd = ["update", path + '@' if '@' in path else path]
        self._add_revision(cmd, kwargs, optional=1)
        status, output = self._execVcs(*cmd, **kwargs)
        if status == 0:
            return [x.split() for x in output.split()]
        return None

    def merge(self, url1, url2=None, rev1=None, rev2=None, path=None, 
            **kwargs):
        cmd = ["merge"]
        if rev1 and rev2 and not url2:
            cmd.append("-r")
            cmd.append("%s:%s" % (rev1, rev2))
            cmd.append(url1)
        else:
            if not url2:
                raise ValueError("url2 needed if two revisions are not provided")
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
        status, output = self._execVcs(*cmd, **kwargs)
        if status == 0:
            return [x.split() for x in output.split()]
        return None

    def diff(self, pathurl1, pathurl2=None, **kwargs):
        cmd = ["diff", pathurl1]
        self._add_revision(cmd, kwargs, optional=1)
        if pathurl2:
            cmd.append(pathurl2)
        status, output = self._execVcs(*cmd, **kwargs)
        if status == 0:
            return output
        return None

    def cat(self, url, **kwargs):
        cmd = ["cat", url]
        self._add_revision(cmd, kwargs, optional=1)
        status, output = self._execVcs(*cmd, **kwargs)
        if status == 0:
            return output
        return None

    def log(self, url, start=None, end=0, limit=None, **kwargs):
        cmd = ["log", "-v", url]
        if start is not None or end != 0:
            if start is not None and type(start) is not type(0):
                try:
                    start = int(start)
                except (ValueError, TypeError):
                    raise Error("invalid log start revision provided")
            if type(end) is not type(0):
                try:
                    end = int(end)
                except (ValueError, TypeError):
                    raise Error("invalid log end revision provided")
            start = start or "HEAD"
            cmd.extend(("-r", "%s:%s" % (start, end)))
        if limit is not None:
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                raise Error("invalid limit number provided")
            cmd.extend(("--limit", str(limit)))

        status, output = self._execVcs(*cmd, xml=True, **kwargs)
        if status != 0:
            return None

        xmllog = ElementTree.fromstring(output)
        log = []
        logentries = xmllog.getiterator("logentry")
        for entry in logentries:
            changed = []
            lines = []
            for pathelem in entry.getiterator("paths"):
                path = pathelem.find("path")
                from_rev = path.get("copyfrom-rev")
                if from_rev:
                    from_rev = int(from_rev)
                changed.append({"from_rev" : from_rev, "from_path" : path.get("copyfrom-path"), "action" : path.get("action"), "path" : path.text})
            date = entry.findtext("date").split("T")
            timestr = "%s %s" % (date[0], date[1].split(".")[0])
            timetuple = time.strptime(timestr, "%Y-%m-%d %H:%M:%S")
            lines.extend(entry.findtext("msg").rstrip().split("\n"))
            logentry = VCSLogEntry(int(entry.attrib["revision"]),
                    entry.findtext("author"), timetuple, [line.rstrip() for line in lines], changed)
            log.append(logentry)
        log.sort()
        log.reverse()
        return log

    def mv(self, path, dest, message=None, **kwargs):
        cmd = ["mv", path, dest,  ]
        if message:
            cmd.extend(("-m", str(message)))
        else:
            kwargs['show'] = True
        self._add_log(cmd, kwargs)
        return self._execVcs_success(*cmd, **kwargs)

    def get_topdir(self):
        vcsdir = os.path.join(self._path, self.vcs_dirname)
        if os.path.exists(vcsdir) and os.path.isdir(vcsdir):
            return self._path
        else:
            return None

    @property
    def path(self):
        return self._path

    @property
    def url(self):
        if not self._url:
            self._url = self.info2(self._path)["URL"]
        return self._url

class VCSLook(object):
    def __init__(self, repospath, txn=None, rev=None):
        self.repospath = repospath
        self.txn = txn
        self.rev = rev
        self.execcmd = None

    def _execVcslook(self, cmd, *args, **kwargs):
        execcmd_args = ["svnlook", cmd, self.repospath]
        self._add_txnrev(execcmd_args, kwargs)
        execcmd_args += args
        execcmd_kwargs = {}
        keywords = ["show", "noerror"]
        for key in keywords:
            if key in kwargs:
                execcmd_kwargs[key] = kwargs[key]
        return execcmd(*execcmd_args, **execcmd_kwargs)

    def _add_txnrev(self, cmd_args, received_kwargs):
        if "txn" in received_kwargs:
            txn = received_kwargs.get("txn")
            if txn is not None:
                cmd_args.extend(("-t", txn))
        elif self.txn is not None:
            cmd_args.extend(("-t", self.txn))
        if "rev" in received_kwargs:
            rev = received_kwargs.get("rev")
            if rev is not None:
                cmd_args.exten(("-r", str(rev)))
        elif self.rev is not None:
            cmd_args.extend(("-r", str(self.rev)))

    def changed(self, **kwargs):
        status, output = self._execVcslook("changed", **kwargs)
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
        status, output = self._execVcslook("author", **kwargs)
        if status != 0:
            return None
        return output.strip()

# vim:et:ts=4:sw=4
