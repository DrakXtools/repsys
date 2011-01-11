"""
A mgarepo plugin for obtaining users from a LDAP server.

In order to enable the plugin, the user must define the following 
options in the [global] section of mgarepo.conf:

    ldap-uri [required if ldap-server is unset]
        the URI of the server, you can refer to more than one server by
        adding more URIs separated by spaces::

          ldap-uri = ldap://ldap.network/ ldaps://backup.network:22389/

    ldap-server [required if ldap-uri is unset]
        the host name of the LDAP server
    ldap-port [optional] [default: 389]
        the port of the LDAP server
    ldap-base [required]
        the base DN where the search will be performed
    ldap-binddn [optional] [default: empty]
        the DN used to bind
    ldap-bindpw [optional] [default: empty]
        the password used to bind
    ldap-starttls [optional] [default: no]
         use "yes" or "no" to enable or disable the use of the STARTTLS
         LDAP extension
    ldap-filterformat [optional] 
            [default: (&(objectClass=inetOrgPerson)(uid=$username))]
        RFC-2254 filter string used in the search of the user entry.
        Note that this is a python template string and will have the 
        user name as parameter. For example:

           ldap-filterformat = (&(objectClass=inetOrgPerson)(uid=$username))

        Will result in the search filter:

           (&(objectClass=inetOrgPerson)(uid=john))

    ldap-resultformat [optional] [default: $cn <$mail>]
        This is a python template string. This string will be 
        formatted using one dict object containing the fields
        returned in the LDAP search, for example:

          >>> format = Template("$cn <$mail>")
          >>> d = search(basedn, filter)
          >>> d
          {"cn": "John Doe", "mail": "john@mandriva.org", 
           "uidNumber": "1290", "loginShell": "/bin/bash", 
            ... many other attributes ... }
          >>> value = format.substitute(d)
          >>> print value
          John Doe <john@mandriva.org>

        Note that only the first value of the attributes will be 
        used.

When the searched option is not found, it will try in mgarepo.conf. All
the values found.  (including from mgarepo.conf) will be cached between
each configuration access.

This plugin requires the package python-ldap.

For more information, look http://qa.mandriva.com/show_bug.cgi?id=30549
"""
from MgaRepo import Error, config

import string

users_cache = {}

class LDAPError(Error):
    def __init__(self, ldaperr):
        self.ldaperr = ldaperr
        name = ldaperr.__class__.__name__
        desc = ldaperr.message["desc"]
        self.message = "LDAP error %s: %s" % (name, desc)
        self.args = self.message,

def strip_entry(entry):
    "Leave only the first value in all keys in the entry"
    new = dict((key, value[0]) for key, value in entry.iteritems())
    return new

def interpolate(optname, format, data):
    tmpl = string.Template(format)
    try:
        return tmpl.substitute(data)
    except KeyError, e:
        raise Error, "the key %s was not found in LDAP search, " \
                "check your %s configuration" % (e, optname)
    except (TypeError, ValueError), e:
        raise Error, "LDAP response formatting error: %s. Check " \
                "your %s configuration" % (e, optname)

def used_attributes(format):
    class DummyDict:
        def __init__(self):
            self.found = []
        def __getitem__(self, key):
            self.found.append(key)
            return key
    dd = DummyDict()
    t = string.Template(format)
    t.safe_substitute(dd)
    return dd.found

def make_handler():
    uri = config.get("global", "ldap-uri")
    if not uri:
        server = config.get("global", "ldap-server")
        if not server:
            # ldap support is not enabled if ldap-uri nor ldap-server are
            # defined
            def dummy_wrapper(section, option=None, default=None, walk=False):
                return config.get(section, option, default, wrap=False)
            return dummy_wrapper

        try:
            port = int(config.get("global", "ldap-port", 389))
        except ValueError:
            raise Error, "the option ldap-port requires an integer, please "\
                    "check your configuration files"
        uri = "ldap://%s:%d" % (server, port)

    basedn = config.get("global", "ldap-base")
    binddn = config.get("global", "ldap-binddn")
    bindpw = config.get("global", "ldap-bindpw", "")
    filterformat = config.get("global", "ldap-filterformat",
            "(&(objectClass=inetOrgPerson)(uid=$username))", raw=1)
    format = config.get("global", "ldap-resultformat", "$cn <$mail>", raw=1)

    valid = {"yes": True, "no": False}
    raw = config.get("global", "ldap-starttls", "no")
    try:
        starttls = valid[raw]
    except KeyError:
        raise Error, "invalid value %r for ldap-starttls, use "\
                "'yes' or 'no'" % raw

    try:
        import ldap
    except ImportError:
        raise Error, "LDAP support needs the python-ldap package "\
                "to be installed"
    else:
        from ldap.filter import escape_filter_chars

    def users_wrapper(section, option=None, default=None, walk=False):
        global users_cache
        if walk:
            raise Error, "ldapusers plugin does not support user listing"
        assert option is not None, \
                "When not section walking, option is required"

        value = users_cache.get(option)
        if value is not None:
            return value

        try:
            l = ldap.initialize(uri)
            if starttls:
                l.start_tls_s()
            if binddn:
                l.bind(binddn, bindpw)
        except ldap.LDAPError, e:
            raise LDAPError(e)
        try:
            data = {"username": escape_filter_chars(option)}
            filter = interpolate("ldap-filterformat", filterformat, data)
            attrs = used_attributes(format)
            try:
                found = l.search_s(basedn, ldap.SCOPE_SUBTREE, filter,
                        attrlist=attrs)
            except ldap.LDAPError, e:
                raise LDAPError(e)
            if found:
                dn, entry = found[0]
                entry = strip_entry(entry)
                value = interpolate("ldap-resultformat", format, entry)
            else:
                # issue a warning?
                value = config.get(section, option, default, wrap=False)
            users_cache[option] = value
            return value
        finally:
            l.unbind_s()

    return users_wrapper

config.wrap("users", handler=make_handler())
