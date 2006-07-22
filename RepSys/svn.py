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

    def _log_handler(self):
        if self._current_message is None:
            raise ValueError, "No log message defined"
        return True, self._current_message

    def _get_log_message(self, received_kwargs):
        message = received_kwargs.pop("log", None)
        messagefile = received_kwargs.pop("logfile", None)
        if messagefile and not message:
            message = open(messagefile).read()
        return message
            
    def _make_wrapper(self, meth):
        def wrapper(*args, **kwargs):
            self._client_lock.acquire()
            try:
                self._current_message = self._get_log_message(kwargs)
                ignore_errors = kwargs.pop("noerror", None)
                try:
                    return meth(*args, **kwargs)
                except pysvn.ClientError, (msg,):
                    if not ignore_errors:
                        raise SVNError, msg
                    return None
            finally:
                self._current_message = None
                self._client_lock.release()
        return wrapper

    def __getattr__(self, attrname):
        meth = getattr(self._client, attrname)
        wrapper = self._make_wrapper(meth)
        return wrapper

    def revision(number=None, head=None):
        if number is not None:
            args = (pysvn.opt_revision_kind.number, number)
        else:
            args = (pysvn.opt_revision_kind.head,)
        return pysvn.Revision(*args)
    revision = staticmethod(revision)

    # this override method fixed the problem in pysvn's mkdir which
    # requires a log_message parameter
    def mkdir(self, path, log=None, **kwargs):
        meth = self.__getattr__("mkdir")
        # we can't raise an error because pysvn's mkdir will use
        # log_message only if path is remote, but it *always* requires this
        # parameter. Also, 'log' is never used.
        log = log or "There's a silent bug in your code"
        return meth(path, log, log=None, **kwargs)

    def checkin(self, path, log, **kwargs):
        # XXX use EDITOR when log empty
        meth = self.__getattr__("checkin")
        return meth(path, log, log=None, **kwargs)

    def log(self, *args, **kwargs):
        meth = self.__getattr__("log")
        entries = meth(*args, **kwargs)
        if entries is None:
            return
        for entrydic in entries:
            entry = SVNLogEntry(entrydic["revision"].number,
                                entrydic["author"],
                                time.localtime(entrydic["date"]))
            entry.lines[:] = entrydic["message"].split("\n")
            yield entry

    def exists(self, path):
        return self.ls(path, noerror=1) is not None

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
            while 1:
                os.system("%s %s" % (editor, fpath))
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
        revision = self.revision(revision)
        if revprop:
            propget = self.revpropget
            propset = self.revpropset
        else:
            propget = self.propget
            propset = self.propset
        revision, message = propget(propname, pkgdirurl, revision=revision)
        changed, newmessage = self._edit_message(message)
        try:
            if changed:
                propset(propname, newmessage, pkgdirurl, revision=revision)
        except pysvn.ClientError, (msg,):
            raise SVNError, msg

# vim:et:ts=4:sw=4
