#!/usr/bin/python
from MgaRepo import Error, config
from MgaRepo.rpmutil import get_srpm
from MgaRepo.cgiutil import CgiError, get_targets
import cgi
import sys
import os

TEMPLATE = """\
<html>
<head>
<title>Repository package submission system</title>
</head>
<body bgcolor="white">
<table cellspacing=0 cellpadding=0 border=0 width="100%%">
  <tr bgcolor="#020264"><td align="left" valign="middle"><img src="http://qa.mandriva.com/mandriva.png" hspace=0 border=0 alt=""></td></tr>
</table>
<br>
<hr>
<center>
<b>%(message)s</b>
<br><br>
<form method="POST" action="">
<table><tr><td valign="top">
  Package URL:<br>
  <input name="packageurl" size="60" value="svn+ssh://cvs.mandriva.com/svn/mdv/cooker/"><br>
  <small>Ex. svn+ssh://cvs.mandriva.com/svn/mdv/cooker/pkgname</small><br>
  </td><td valign="top">
  Revision:<br>
  <input name="packagerev" size="10" value=""><br>
  </td></tr></table>
  <br>
  Package target:<br>
  <select name="target" size=5>
  %(targetoptions)s
  </select><br>
  <br>
  <input type="submit" value="Submit package">
</form>
</center>
<hr/>
</body>
</html>
"""

def get_targetoptions():
    s = ""
    selected = " selected"
    for target in get_targets():
        s += '<option value="%s"%s>%s</option>' \
             % (target.name, selected, target.name)
        selected = ""
    return s
 
def show(msg="", error=0):
    if error:
        msg = '<font color="red">%s</font>' % msg
    print TEMPLATE % {"message":msg, "targetoptions":get_targetoptions()}

def submit_packages(packager):
    form = cgi.FieldStorage()
    packageurl = form.getfirst("packageurl", "").strip()
    packagerev = form.getfirst("packagerev", "").strip()
    if not packageurl:
        show()
    elif not packagerev:
        raise CgiError, "No revision provided!"
    else:
        targetname = form.getfirst("target")
        if not targetname:
            raise CgiError, "No target selected!"
        for target in get_targets():
            if target.name == targetname:
                break
        else:
            raise CgiError, "Target not found!"
        try:
            tmp = int(packagerev)
        except ValueError:
            raise CgiError, "Invalid revision provided!"
        for allowed in target.allowed:
            if packageurl.startswith(allowed):
                break
        else:
            raise CgiError, "%s is not allowed for this target!" % packageurl
        get_srpm(packageurl,
                 revision=packagerev,
                 targetdirs=target.target,
                 packager=packager,
                 revname=1,
                 svnlog=1,
                 scripts=target.scripts)
        show("Package submitted!")

def main():
    if not os.environ.has_key('REQUEST_METHOD'):
        sys.stderr.write("error: this program is meant to be used as a cgi\n")
        sys.exit(1)
    print "Content-type: text/html\n\n"
    try:
        username = os.environ.get("REMOTE_USER")
        method = os.environ.get("REQUEST_METHOD")
        if not username or method != "POST":
            show()
        else:
            useremail = config.get("users", username)
            if not useremail:
                raise CgiError, \
                      "Your email was not found. Contact the administrator!"
            submit_packages(useremail)
    except CgiError, e:
        show(str(e), error=1)
    except Error, e:
        error = str(e)
        show(error[0].upper()+error[1:], error=1)
    except:
        cgi.print_exception()

# vim:et:ts=4:sw=4
