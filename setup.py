#!/usr/bin/python
from distutils.core import setup
import sys
import re

verpat = re.compile("VERSION *= *\"(.*)\"")
data = open("repsys").read()
m = verpat.search(data)
if not m:
    sys.exit("error: can't find VERSION")
VERSION = m.group(1)

setup(name="repsys",
      version = VERSION,
      description = "Tools for Mandriva Linux repository access and management",
      author = "Gustavo Niemeyer",
      author_email = "gustavo@niemeyer.net",
		url = "http://qa.mandriva.com/twiki/bin/view/Main/RepositorySystem",
      license = "GPL",
      long_description = """Tools for Mandriva Linux repository access and management.""",
      packages = ["RepSys", "RepSys.cgi", "RepSys.commands"],
      scripts = ["repsys"],
      data_files = [
	      ("/usr/share/repsys/", 
              ["default.chlog", 
              "revno.chlog", 
              "create-srpm",
              "getsrpm-mdk", 
              "rebrand-mdk"]),
	      ("/etc/", ["repsys.conf"])]
      )

# vim:ts=4:sw=4:et
