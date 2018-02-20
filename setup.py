#!/usr/bin/python3
from setuptools import setup
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
      description = "Tools for repository access and management for Mandrake Linux derived distros",
      author = "Gustavo Niemeyer",
      author_email = "gustavo@niemeyer.net",
      url = "https://github.com/DrakXtools/repsys",
      license = "GPL",
      long_description = """Tools for repository access and management for Mandrake Linux derived distros.""",
      packages = ["RepSys", "RepSys.cgi", "RepSys.commands",
          "RepSys.plugins"],
      scripts = ["repsys", "repsys-ssh"],
      data_files = [
	      ("/usr/share/repsys/",
              ["create-srpm"]),
              ("share/bash-completion/completions",
               ["bash-completion/repsys"]),
	      ("/etc/", ["repsys.conf"]),
          ("share/man/man8/", ["repsys.8"])],
      install_requires=['PyGithub>=1.27.1', 'httplib2', 'rpm-python', 'progressbar2', "PyYAML"]
      )

# vim:ts=4:sw=4:et
