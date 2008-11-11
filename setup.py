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
      packages = ["RepSys", "RepSys.cgi", "RepSys.commands",
          "RepSys.plugins"],
      scripts = ["repsys", "getsrpm-mdk"],
      data_files = [
	      ("/usr/share/repsys/", 
              ["default.chlog", 
              "revno.chlog",
              "oldfashion.chlog",
              "compatv15.chlog",
              "create-srpm",
              "rebrand-mdk"]),
	      ("/etc/", ["repsys.conf"]),
          ("share/man/man8/", ["repsys.8"])]
      )

# vim:ts=4:sw=4:et
