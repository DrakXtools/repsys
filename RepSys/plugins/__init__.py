import os

loaded = {}

def load():
    # based on smart's plugin system 
    pluginsdir = os.path.dirname(__file__)
    for entry in os.listdir(pluginsdir):
        if entry != "__init__.py" and entry.endswith(".py"):
            name = entry[:-3]
            loaded[name] = __import__("RepSys.plugins."+name, {}, {},
                    [name])
        elif os.path.isdir(entry):
            initfile = os.path.join(entry, "__init__.py")
            if os.path.isfile(initfile):
                loaded[entry] = __import__("RepSys.plugins."+entry, {}, {},
                        [entry])

def list():
    return loaded.keys()

def help(name):
    from RepSys import Error
    try:
        return loaded[name].__doc__
    except KeyError:
        raise Error, "plugin %s not found" % name
