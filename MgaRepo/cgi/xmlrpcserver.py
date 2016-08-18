from MgaRepo import Error, config
from MgaRepo.rpmutil import get_srpm
from MgaRepo.cgiutil import CgiError, get_targets
import sys
import os

import xmlrpc.client, cgi

class XmlRpcIface:
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
    username = os.environ.get("REMOTE_USER")
    method = os.environ.get("REQUEST_METHOD")
    if not username or method != "POST":
        show("This is a XMLRPC interface!", error=1)
        sys.exit(1)

    iface = XmlRpcIface()

    response = ""
    try:
        form = cgi.FieldStorage()
        parms, method = xmlrpc.client.loads(form.value)
        meth = getattr(iface, method)
        response = (meth(*parms),)
    except CgiError as e:
        msg = str(e)
        try:
            msg = msg.decode("iso-8859-1")
        except UnicodeError:
            pass
        response = xmlrpc.client.Fault(1, msg)
    except Exception as e:
        msg = str(e)
        try:
            msg = msg.decode("iso-8859-1")
        except UnicodeError:
            pass
        response = xmlrpc.client.Fault(1, msg)

    sys.stdout.write("Content-type: text/xml\n\n")
    sys.stdout.write(xmlrpc.client.dumps(response, methodresponse=1))

# vim:et:ts=4:sw=4
