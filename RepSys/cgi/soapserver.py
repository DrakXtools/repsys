from RepSys import Error, config
from RepSys.rpmutil import get_srpm
from RepSys.cgiutil import CgiError, get_targets
import sys
import os

try:
    import NINZ.dispatch
except ImportError:
    NINZ = None

class SoapIface:
    def author_email(self, author):
        return config.get("users", author)

    def submit_package(self, packageurl, packagerev, targetname):
        username = os.environ.get("REMOTE_USER")
        packager = config.get("users", username)
        if not packager:
            raise CgiError("your email was not found")
        elif not packagerev:
            raise CgiError("no revision provided")
        elif not targetname:
            raise CgiError("no target provided")
        else:
            targetname = targetname.lower()
            for target in get_targets():
                if target.name.lower() == targetname:
                    break
            else:
                raise CgiError("target not found")
            try:
                tmp = int(packagerev)
            except ValueError:
                raise CgiError("invalid revision provided")
            for allowed in target.allowed:
                if packageurl.startswith(allowed):
                    break
            else:
                raise CgiError("%s is not allowed for this target" \
                                % packageurl)
            get_srpm(packageurl,
                     revision=packagerev,
                     targetdirs=target.target,
                     packager=packager,
                     revname=1,
                     svnlog=1,
                     scripts=target.scripts)
        return 1

    def submit_targets(self):
        return [x.name for x in get_targets()]

TEMPLATE = """\
Content-type: text/html

<html>
<head>
<title>Repository system SOAP server</title>
</head>
<body bgcolor="white">
<br>
<hr>
<center>
<b>%(message)s</b>
</center>
<hr>
</body>
</html>
"""

def show(msg="", error=0):
    if error:
        msg = '<font color="red">%s</font>' % msg
    print(TEMPLATE % {"message":msg})

def main():
    if 'REQUEST_METHOD' not in os.environ:
        sys.stderr.write("error: this program is meant to be used as a cgi\n")
        sys.exit(1)
    if not NINZ:
        show("NINZ is not properly installed in this system", error=1)
        sys.exit(1)
    username = os.environ.get("REMOTE_USER")
    method = os.environ.get("REQUEST_METHOD")
    if not username or method != "POST":
        show("This is a SOAP interface!", error=1)
        sys.exit(1)

    NINZ.dispatch.AsCGI(modules=(SoapIface(),))

# vim:et:ts=4:sw=4
