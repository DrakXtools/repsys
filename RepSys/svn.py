from RepSys import Error, config
from RepSys.util import execcmd, get_auth

import sys
import os
import re
import time
import threading
import tempfile
import pysvn

__all__ = ["SVN", "Revision", "SVNLogEntry", "SVNError"]

class SVNError(Error):
    pass

class SVNLogEntry:
    def __init__(self, revision, author, date):
        self.revision = revision
        self.author = author
        self.date = date
        self.changed = []
        self.lines = []

    def __cmp__(self, other):
        return cmp(self.date, other.date)

class SVN:
    _client = None
    _client_lock = None
    _current_message = None

    def __init__(self):
        self._client = pysvn.Client()
        self._client_lock = threading.Lock()
        self._client.callback_get_log_message = self._log_handler
        self._client.callback_get_login = self._unsupported_auth
        self._client.callback_ssl_client_cert_password_prompt = \
                self._unsupported_auth
        self._client.callback_ssl_client_cert_prompt = \
                self._unsupported_auth
        self._client.callback_ssl_server_prompt = \
                self._unsupported_auth

    def _log_handler(self):
        if self._current_message is None:
            #TODO make it use EDITOR
            raise ValueError, "No log message defined"
        return True, self._current_message

    def _unsupported_auth(self, *args, **kwargs):
        raise SVNError, "svn is trying to get login information, " \
                "seems that you're not using ssh-agent"

    def _get_log_message(self, received_kwargs):
        message = received_kwargs.pop("log", None)
        messagefile = received_kwargs.pop("logfile", None)
        if messagefile and not message:
            message = open(messagefile).read()
        return message

    def _set_notify_callback(self, callback):
        self._client.callback_notify = callback

    def _make_wrapper(self, meth, notify=None):
        def wrapper(*args, **kwargs):
            self._client_lock.acquire()
            try:
                self._current_message = self._get_log_message(kwargs)
                ignore_errors = kwargs.pop("noerror", None)
                if notify:
                    self._client.callback_notify = notify
                try:
                    return meth(*args, **kwargs)
                except pysvn.ClientError, (msg,):
                    if not ignore_errors:
                        raise SVNError, msg
                    return None
            finally:
                self._client_lock.release()
                self._current_message = None
        return wrapper

    def _client_wrap(self, attrname):
        meth = getattr(self._client, attrname)
        wrapper = self._make_wrapper(meth)
        return wrapper

    def __getattr__(self, attrname):
        return self._client_wrap(attrname)
    
    def makerev(number=None, head=None):
        if number is not None:
            args = (pysvn.opt_revision_kind.number, number)
        else:
            args = (pysvn.opt_revision_kind.head,)
        return pysvn.Revision(*args)
    makerev = staticmethod(makerev)

    def revision(self, url, last_changed=False):
        infos = self._client.info2(url, recurse=False)
        if last_changed:
            revnum = infos[0][1].last_changed_rev.number
        else:
            revnum = infos[0][1].rev.number
        return revnum

    # this override method fixed the problem in pysvn's mkdir which
    # requires a log_message parameter
    def mkdir(self, path, log=None, **kwargs):
        meth = self._client_wrap("mkdir")
        # we can't raise an error because pysvn's mkdir will use
        # log_message only if path is remote, but it *always* requires this
        # parameter. Also, 'log' is never used.
        log = log or "There's a silent bug in your code"
        return meth(path, log, log=None, **kwargs)
    
    def checkout(self, url, targetpath, show=False, **kwargs):
        if show:
            def callback(event):
                types = pysvn.wc_notify_action
                action = event["action"]
                if action == types.update_add:
                    print "A    %s" % event["path"]
                elif action == types.update_completed:
                    print "Checked out revision %d" % \
                            event["revision"].number
            self._set_notify_callback(callback)
        meth = self._client_wrap("checkout")
        meth(url, targetpath, **kwargs)

    def checkin(self, path, log, **kwargs):
        # XXX use EDITOR when log empty
        meth = self._client_wrap("checkin")
        return meth(path, log, log=None, **kwargs)
    
    def log(self, *args, **kwargs):
        meth = self._client_wrap("log")
        entries = meth(discover_changed_paths=True, *args, **kwargs)
        if entries is None:
            return
        for entrydic in entries:
            entry = SVNLogEntry(entrydic["revision"].number,
                                entrydic["author"],
                                time.localtime(entrydic["date"]))
            entry.lines[:] = entrydic["message"].split("\n")
            for cp in entrydic["changed_paths"]:
                from_rev = cp["copyfrom_revision"]
                if from_rev:
                    from_rev = from_rev.number
                changed = {
                    "action": cp["action"],
                    "path": cp["path"],
                    "from_rev": from_rev,
                    "from_path": cp["copyfrom_path"],
                }
                entry.changed.append(changed)
            yield entry
    
    def exists(self, path):
        return self.ls(path, noerror=1) is not None

    def status(self, *args, **kwargs):
        # add one keywork "silent" that workaround the strange behavior of
        # pysvn's get_all, which seems to be broken, this way we also have
        # the same interface of svn.py from repsys 1.6.x
        meth = self._client_wrap("status")
        silent = kwargs.pop("silent", None)
        st = meth(*args, **kwargs)
        if silent:
            unversioned = pysvn.wc_status_kind.unversioned
            st = [entry for entry in st
                    if entry.text_status is not unversioned]
        return st

    def diff(self, path1, *args, **kwargs):
        head = pysvn.Revision(pysvn.opt_revision_kind.head)
        revision1 = kwargs.pop("revision1", head)
        revision2 = kwargs.pop("revision2", head)
        if args:
            kwargs["url_or_path2"] = args[0]
        tmpdir = tempfile.gettempdir()
        meth = self._client_wrap("diff")
        diff_text = meth(tmpdir, path1, revision1=revision1,
                revision2=revision2, **kwargs)
        return diff_text

    def _edit_message(self, message):
        # argh!
        editor = os.getenv("EDITOR", "vim")
        fd, fpath = tempfile.mkstemp(prefix="repsys")
        result = (False, None)
        try:
            f = os.fdopen(fd, "w")
            f.write(message)
            f.close()
            lastchange = os.stat(fpath).st_mtime
            for i in xrange(10):
                status = os.system("%s %s" % (editor, fpath))
                if status != 0:
                    raise SVNError, "the editor failed with %d" % status
                newchange = os.stat(fpath).st_mtime
                if newchange == lastchange:
                    print "Log message unchanged or not specified"
                    print "(a)bort, (c)ontinue, (e)dit"
                    choice = raw_input()
                    if not choice or choice[0] == 'e':
                        continue
                    elif choice[0] == 'a':
                        break
                    elif choice[0] == 'c':
                        pass # ignore and go ahead
                newmessage = open(fpath).read()
                result = (True, newmessage)
                break
        finally:
            os.unlink(fpath)
        return result

    def propedit(self, propname, pkgdirurl, revision, revprop=False):
        revision = (revision)
        if revprop:
            propget = self.revpropget
            propset = self.revpropset
        else:
            propget = self.propget
            propset = self.propset
        revision, message = propget(propname, pkgdirurl, revision=revision)
        changed, newmessage = self._edit_message(message)
        if changed:
            propset(propname, newmessage, pkgdirurl, revision=revision)

# vim:et:ts=4:sw=4
