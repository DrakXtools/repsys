"""
This is a heavily hacked version of ConfigParser to keep the order in 
which options and sections are read, and allow multiple options with
the same key.
"""
from __future__ import generators
import string, types
import re

__all__ = ["NoSectionError","DuplicateSectionError","NoOptionError",
           "InterpolationError","InterpolationDepthError","ParsingError",
           "MissingSectionHeaderError","ConfigParser",
           "MAX_INTERPOLATION_DEPTH"]

DEFAULTSECT = "DEFAULT"

MAX_INTERPOLATION_DEPTH = 10

# exception classes
class Error(Exception):
    def __init__(self, msg=''):
        self._msg = msg
        Exception.__init__(self, msg)
    def __repr__(self):
        return self._msg
    __str__ = __repr__

class NoSectionError(Error):
    def __init__(self, section):
        Error.__init__(self, 'No section: %s' % section)
        self.section = section

class DuplicateSectionError(Error):
    def __init__(self, section):
        Error.__init__(self, "Section %s already exists" % section)
        self.section = section

class NoOptionError(Error):
    def __init__(self, option, section):
        Error.__init__(self, "No option `%s' in section: %s" %
                       (option, section))
        self.option = option
        self.section = section

class InterpolationError(Error):
    def __init__(self, reference, option, section, rawval):
        Error.__init__(self,
                       "Bad value substitution:\n"
                       "\tsection: [%s]\n"
                       "\toption : %s\n"
                       "\tkey    : %s\n"
                       "\trawval : %s\n"
                       % (section, option, reference, rawval))
        self.reference = reference
        self.option = option
        self.section = section

class InterpolationDepthError(Error):
    def __init__(self, option, section, rawval):
        Error.__init__(self,
                       "Value interpolation too deeply recursive:\n"
                       "\tsection: [%s]\n"
                       "\toption : %s\n"
                       "\trawval : %s\n"
                       % (section, option, rawval))
        self.option = option
        self.section = section

class ParsingError(Error):
    def __init__(self, filename):
        Error.__init__(self, 'File contains parsing errors: %s' % filename)
        self.filename = filename
        self.errors = []

    def append(self, lineno, line):
        self.errors.append((lineno, line))
        self._msg = self._msg + '\n\t[line %2d]: %s' % (lineno, line)

class MissingSectionHeaderError(ParsingError):
    def __init__(self, filename, lineno, line):
        Error.__init__(
            self,
            'File contains no section headers.\nfile: %s, line: %d\n%s' %
            (filename, lineno, line))
        self.filename = filename
        self.lineno = lineno
        self.line = line

class ConfigParser:
    def __init__(self, defaults=None):
        # Options are stored in __sections_list like this:
        # [(sectname, [(optname, optval), ...]), ...]
        self.__sections_list = []
        self.__sections_dict = {}
        if defaults is None:
            self.__defaults = {}
        else:
            self.__defaults = defaults

    def defaults(self):
        return self.__defaults

    def sections(self):
        return self.__sections_dict.keys()

    def has_section(self, section):
        return self.__sections_dict.has_key(section)

    def options(self, section):
        self.__sections_dict[section]
        try:
            opts = self.__sections_dict[section].keys()
        except KeyError:
            raise NoSectionError(section)
        return self.__defaults.keys()+opts

    def read(self, filenames):
        if type(filenames) in types.StringTypes:
            filenames = [filenames]
        for filename in filenames:
            try:
                fp = open(filename)
            except IOError:
                continue
            self.__read(fp, filename)
            fp.close()

    def readfp(self, fp, filename=None):
        if filename is None:
            try:
                filename = fp.name
            except AttributeError:
                filename = '<???>'
        self.__read(fp, filename)

    def set(self, section, option, value):
        if self.__sections_dict.has_key(section):
            sectdict = self.__sections_dict[section]
            sectlist = []
            self.__sections_list.append((section, sectlist))
        elif section == DEFAULTSECT:
            sectdict = self.__defaults
            sectlist = None
        else:
            sectdict = {}
            self.__sections_dict[section] = sectdict
            sectlist = []
            self.__sections_list.append((section, sectlist))
        xform = self.optionxform(option)
        sectdict[xform] = value
        if sectlist is not None:
            sectlist.append([xform, value])

    def get(self, section, option, raw=0, vars=None):
        d = self.__defaults.copy()
        try:
            d.update(self.__sections_dict[section])
        except KeyError:
            if section != DEFAULTSECT:
                raise NoSectionError(section)
        if vars:
            d.update(vars)
        option = self.optionxform(option)
        try:
            rawval = d[option]
        except KeyError:
            raise NoOptionError(option, section)
        if raw:
            return rawval
        return self.__interpolate(rawval, d)

    def getall(self, section, option, raw=0, vars=None):
        option = self.optionxform(option)
        values = []
        d = self.__defaults.copy()
        if section != DEFAULTSECT:
            for sectname, options in self.__sections_list:
                if sectname == section:
                    for optname, value in options:
                        if optname == option:
                            values.append(value)
                        d[optname] = value
        if raw:
            return values
        if vars:
            d.update(vars)
        for i in len(values):
            values[i] = self.__interpolate(values[i], d)
        return values

    def walk(self, section, option=None, raw=0, vars=None):
        # Build dictionary for interpolation
        try:
            d = self.__sections_dict[section].copy()
        except KeyError:
            if section == DEFAULTSECT:
                d = {}
            else:
                raise NoSectionError(section)
        d.update(self.__defaults)
        if vars:
            d.update(vars)

        # Start walking
        if option:
            option = self.optionxform(option)
        if section != DEFAULTSECT:
            for sectname, options in self.__sections_list:
                if sectname == section:
                    for optname, value in options:
                        if not option or optname == option:
                            if not raw:
                                value = self.__interpolate(value, d)
                            yield (optname, value)

    def __interpolate(self, value, vars):
        rawval = value
        depth = 0
        while depth < 10:
            depth = depth + 1
            if value.find("%(") >= 0:
                try:
                    value = value % vars
                except KeyError, key:
                    raise InterpolationError(key, option, section, rawval)
            else:
                break
        if value.find("%(") >= 0:
            raise InterpolationDepthError(option, section, rawval)
        return value

    def __get(self, section, conv, option):
        return conv(self.get(section, option))

    def getint(self, section, option):
        return self.__get(section, string.atoi, option)

    def getfloat(self, section, option):
        return self.__get(section, string.atof, option)

    def getboolean(self, section, option):
        states = {'1': 1, 'yes': 1, 'true': 1, 'on': 1,
                  '0': 0, 'no': 0, 'false': 0, 'off': 0}
        v = self.get(section, option)
        if not states.has_key(v.lower()):
            raise ValueError, 'Not a boolean: %s' % v
        return states[v.lower()]

    def optionxform(self, optionstr):
        #return optionstr.lower()
        return optionstr

    def has_option(self, section, option):
        """Check for the existence of a given option in a given section."""
        if not section or section == "DEFAULT":
            return self.__defaults.has_key(option)
        elif not self.has_section(section):
            return 0
        else:
            option = self.optionxform(option)
            return self.__sections_dict[section].has_key(option)

    SECTCRE = re.compile(r'\[(?P<header>[^]]+)\]')
    OPTCRE = re.compile(r'(?P<option>\S+)\s*(?P<vi>[:=])\s*(?P<value>.*)$')

    def __read(self, fp, fpname):
        cursectdict = None                            # None, or a dictionary
        optname = None
        lineno = 0
        e = None                                  # None, or an exception
        while 1:
            line = fp.readline()
            if not line:
                break
            lineno = lineno + 1
            # comment or blank line?
            if line.strip() == '' or line[0] in '#;':
                continue
            if line.split()[0].lower() == 'rem' \
               and line[0] in "rR":      # no leading whitespace
                continue
            # continuation line?
            if line[0] in ' \t' and cursectdict is not None and optname:
                value = line.strip()
                if value:
                    k = self.optionxform(optname)
                    cursectdict[k] = "%s\n%s" % (cursectdict[k], value)
                    cursectlist[-1][1] = "%s\n%s" % (cursectlist[-1][1], value)
            # a section header or option header?
            else:
                # is it a section header?
                mo = self.SECTCRE.match(line)
                if mo:
                    sectname = mo.group('header')
                    if self.__sections_dict.has_key(sectname):
                        cursectdict = self.__sections_dict[sectname]
                        cursectlist = []
                        self.__sections_list.append((sectname, cursectlist))
                    elif sectname == DEFAULTSECT:
                        cursectdict = self.__defaults
                        cursectlist = None
                    else:
                        cursectdict = {}
                        self.__sections_dict[sectname] = cursectdict
                        cursectlist = []
                        self.__sections_list.append((sectname, cursectlist))
                    # So sections can't start with a continuation line
                    optname = None
                # no section header in the file?
                elif cursectdict is None:
                    raise MissingSectionHeaderError(fpname, lineno, `line`)
                # an option line?
                else:
                    mo = self.OPTCRE.match(line)
                    if mo:
                        optname, vi, optval = mo.group('option', 'vi', 'value')
                        if vi in ('=', ':') and ';' in optval:
                            # ';' is a comment delimiter only if it follows
                            # a spacing character
                            pos = optval.find(';')
                            if pos and optval[pos-1] in string.whitespace:
                                optval = optval[:pos]
                        optval = optval.strip()
                        # allow empty values
                        if optval == '""':
                            optval = ''
                        xform = self.optionxform(optname)
                        cursectdict[xform] = optval
                        if cursectlist is not None:
                            cursectlist.append([xform, optval])
                    else:
                        # a non-fatal parsing error occurred.  set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        if not e:
                            e = ParsingError(fpname)
                        e.append(lineno, `line`)
        # if any parsing errors occurred, raise an exception
        if e:
            raise e

# Here we wrap this hacked ConfigParser into something more useful
# for us.

import os

class Config:
    def __init__(self):
        self._config = ConfigParser()
        conffiles = []
        conffiles.append("/etc/repsys.conf")
        repsys_conf = os.environ.get("REPSYS_CONF")
        if repsys_conf:
            conffiles.append(repsys_conf)
        conffiles.append(os.path.expanduser("~/.repsys/config"))
        for file in conffiles:
            if os.path.isfile(file):
                self._config.read(file)

    def sections(self):
        try:
            return self._config.sections()
        except Error:
            return []

    def options(self, section):
        try:
            return self._config.options(section)
        except Error:
            return []

    def set(self, section, option, value):
        return self._config.set(section, option, value)
    
    def walk(self, section):
        return self._config.walk(section)

    def get(self, section, option, default=None):
        try:
            return self._config.get(section, option)
        except Error:
            return default
    
    def getint(self, section, option, default=None):
        ret = self.get(section, option, default)
        if type(ret) == type(""):
            return int(ret)
            
    def getbool(self, section, option, default=None):
        ret = self.get(section, option, default)
        states = {'1': 1, 'yes': 1, 'true': 1, 'on': 1,
                  '0': 0, 'no': 0, 'false': 0, 'off': 0}
        if type(ret) == type("") and states.has_key(ret.lower()):
            return states[ret.lower()]
        return default

# vim:ts=4:sw=4:et
