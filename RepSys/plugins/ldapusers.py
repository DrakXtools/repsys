"""
A Repsys plugin for obtaining users from a LDAP server.

In order to enable the plugin, the user must define the following 
options the [global] section of repsys.conf:

    ldap-server [required]
        the host name of the LDAP server
    ldap-port [optional] [default: 389]
        the port of the LDAP server
    ldap-base [required]
        the base DN where the search will be performed
    ldap-binddn [optional] [default: empty]
        the DN used to bind
    ldap-bindpw [optional] [default: empty]
        the password used to bind
    ldap-filterformat [optional] 
                      [default: (&(objectClass=inetOrgPerson)(uid=%s))]
        RFC-2254 filter string used in the search of the user entry.
        Note that this is a python format string and will have the user
        name as parameter. For example:

           ldap-filterformat = (&(objectClass=inetOrgPerson)(uid=%s))

        Will result in the search filter:

           (&(objectClass=inetOrgPerson)(uid=john))

    ldap-format [optional] [default: %(cn)s <%(mail)s>]
        This is a python format string. This string will be 
        formatted using one dict object containing the fields
        returned in the LDAP search, for example:

          >>> format = "%(cn)s <%(mail)s>"
          >>> d = search(basedn, filter)
          >>> d = {"cn": "John Doe", "mail": "john@mandriva.org", 
                   "uidNumber": "1290", "loginShell": "/bin/bash", 
                   ... many other attributes ... }
          >>> value = format % d
          >>> print value
          John Doe <john@mandriva.org>

        Note that only the first value of the attributes will be 
        used.

When the searched option is not found, it will try in repsys.conf. All
the values found.  (including from repsys.conf) will be cached between
each configuration access.

This plugin requires the package python-ldap.

For more information, look http://qa.mandriva.com/show_bug.cgi?id=30549
"""
from RepSys import Error, config

users_cache = {}

def strip_entry(entry):
    "Leave only the first value in all keys in the entry"
    new = dict((key, value[0]) for key, value in entry.iteritems())
    return new


def make_handler():
    server = config.get("global", "ldap-server")
    port = config.get("global", "ldap-port")
    basedn = config.get("global", "ldap-base")
    binddn = config.get("global", "ldap-binddn")
    bindpw = config.get("global", "ldap-bindpw", "")
    filterformat = config.get("global", "ldap-filterformat",
            "(&(objectClass=inetOrgPerson)(uid=%s))", raw=1)
    format = config.get("global", "ldap-format", "%(cn)s <%(mail)s>", raw=1)

    if server is None:
        def dummy_wrapper(section, option=None, default=None, walk=False):
            return config.get(section, option, default, wrap=False)
        return dummy_wrapper

    # only load ldap if it is enabled in configuration, this way we don't
    # require everyone to have python-ldap installed
    import ldap

    def users_wrapper(section, option=None, default=None, walk=False):
        global users_cache
        if walk:
            raise Error, "ldapusers plugin does not support user listing"
        assert option is not None, \
                "When not section walking, option is required"

        value = users_cache.get(option)
        if value is not None:
            return value

        l = ldap.open(server)
        if binddn:
            l.bind(binddn, bindpw)
        filter = filterformat % option
        found = l.search_s(basedn, ldap.SCOPE_SUBTREE, filter)
        if found:
            dn, entry = found[0]
            entry = strip_entry(entry)
            try:
                value = format % entry
            except KeyError, e:
                raise Error, "the key %s was not found in LDAP search, " \
                        "check your ldap-format configuration" % e
            except (TypeError, ValueError), e:
                raise Error, "LDAP response formatting error: %s. Check " \
                        "your ldap-format configuration" % e
        else:
            # issue a warning?
            value = config.get(section, option, default, wrap=False)
        users_cache[option] = value
        return value

    return users_wrapper

config.wrap("users", handler=make_handler())
