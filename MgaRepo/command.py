#!/usr/bin/python
from MgaRepo import SilentError, Error, config
import sys, os
import urlparse
import optparse

__all__ = ["OptionParser", "do_command", "default_parent"]

class CapitalizeHelpFormatter(optparse.IndentedHelpFormatter):

    def format_usage(self, usage):
        return optparse.IndentedHelpFormatter \
                .format_usage(self, usage).capitalize()

    def format_heading(self, heading):
        return optparse.IndentedHelpFormatter \
                .format_heading(self, heading).capitalize()

class OptionParser(optparse.OptionParser):

    def __init__(self, usage=None, help=None, **kwargs):
        if not "formatter" in kwargs:
            kwargs["formatter"] = CapitalizeHelpFormatter()
        optparse.OptionParser.__init__(self, usage, **kwargs)
        self._overload_help = help

    def format_help(self, formatter=None):
        if self._overload_help:
            return self._overload_help
        else:
            return optparse.OptionParser.format_help(self, formatter)

    def error(self, msg):
        raise Error, msg

def do_command(parse_options_func, main_func):
    try:
        opt = parse_options_func()
        main_func(**opt.__dict__)
    except SilentError:
        sys.exit(1)
    except Error, e:
        sys.stderr.write("error: %s\n" % str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        sys.stderr.write("interrupted\n")
        sys.stderr.flush()
        sys.exit(1)

def default_parent(url):
    if url.find("://") == -1:
        default_parent = config.get("global", "default_parent")
        if not default_parent:
            raise Error, "received a relative url, " \
                         "but default_parent was not setup"
        parsed = list(urlparse.urlparse(default_parent))
        parsed[2] = os.path.normpath(parsed[2] + "/" + url)
        url = urlparse.urlunparse(parsed)
    return url

# vim:et:ts=4:sw=4
