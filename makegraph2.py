#!/usr/bin/env python

"""
Create a dot file (graphviz)  showing called modules by a python script. For Python 2 code
USE: ./makegraph.py mysteriousscript.py
"""

from __future__ import print_function

import re
import sys
import fileinput

from imp import find_module, is_builtin, is_frozen
#deprecated but works.
#from importlib import import_module #not deprecated but f*** doesn't work
#from modulefinder import ModuleFinder

import pypeline.tools


#try:
#    import matplotlib.pyplot
#except ImportError as e:
#    print("Cannot import matplotlib.pyplot")



#def importedModules(filename):
#    """Return imported modules in a python file"""
#    modules = []
#    for line in fileinput.input([filename]):
#        m = re.search("^\s*import \S+", line) or \
#                re.search("\s*^from \S+", line)
#        if m:
#            modulename = re.search("\S+$", m.group(0)).group(0)
#            #modules.append(modulename)
#            modules.append(findModule(modulename))
#    return modules

def importedModules(filename):
    """Return imported modules in a python file"""
    modules = []
    for line in fileinput.input([filename]):
        m_import = re.search("^\s*import \S+", line)
        m_importas = re.search("^\s*import \S+ as \S+$", line)
        m_fromimport = re.search("^\s*from \S+ import .*$", line)
        if m_import:
            modulename = re.search("\S+$", m_import.group(0)).group(0)
            #modules.append(modulename)
            modules.append(findModule(modulename))
        if m_importas:
            modulename = re.search('(?<=import )\S+', line).group(0)
            abbrv = re.search('(?<= as )\S+', line).group(0)
            modules.append(findModule(modulename))
            modules[-1]["as"] = abbrv
        if m_fromimport:
            modulename = re.search("(?<=from )\S+", line).group(0)
            importedFct = re.search("(?<= import ).*$", line).group(0).\
                    split(", ")
            modules.append(findModule(modulename))
            modules[-1]["importedFct"] = importedFct
    return modules


def findModule(modulename):
    """prints path to module"""
    modules = modulename.split(".")
    path = sys.path
    for m in modules:
        if is_builtin(m):
            return {"name": modulename, "type": "Builtin"}
        elif is_frozen(m):
            return {"name": modulename, "type": "Frozen"}
        else:
            try:
                p = find_module(m, path)
                path.append(p[1])
                #print("adding path %s to path list" % p)
                #print("path list = %s" %path)
            except ImportError:
                return {"name": modulename,
                        "type":"Not Found (ImportError)"}
            if p[1].startswith("/usr/local/"):
                type = "Local"
            else:
                type = "Installed"
    return {"name": modulename,
        "type": type,
        "file": p[0],
        "path": p[1],
        "details": p[2]} #p is a tuple:
                            #(file, filename, (suffixe, mode, type))
                            #exemple from "os":
            #(<open file '/usr/lib/python2.7/os.py' mode 'U' at 0x7f..>,
                            #'/usr/lib/python2.7/os.py',
                            #('.py', 'U', 1))


def main(_argv):
    #modules = importedModules(_argv)
    #print(modules)
    #for m in modules:
    #   print(m + " : " + findModule(m))
    print("digraph \"%s\" {\n" % _argv)
    untested = importedModules(_argv)
    tested = []
    for mod in untested:
        print ("\"%s\" -> \"%s\"" %(_argv, mod["name"]))
    while len(untested) > 0:
        fromfile = untested[0]
        if fromfile["type"] in ["Builtin", "Frozen",
                "Not Found (ImportError)"]:
            pass
        elif fromfile["type"] == "Installed":
            pass
        else:
            try:
                newmodules = importedModules(fromfile["path"])
                for new in newmodules:
                    print("\"%s\" -> \"%s\"" %(fromfile["name"],
                                                        new["name"]))
                    if new not in untested + tested:
                        untested.append(new)
            except IOError as e:
                print(e, file=sys.stderr)
                print("Wrong file was %s" % (fromfile["path"]),
                        file=sys.stderr)
            except KeyError as e:
                print(e, file=sys.stderr)
                print("Dictionary is: %s" %fromfile, file=sys.stderr)
            #untested += newmodules  #I should avoid adding one module that has already been tested.
        tested.append(fromfile)
        untested = untested[1:]
    print("\n}\n")

if __name__ == '__main__':
   sys.exit(main(sys.argv[1]))

#print(importedModules(sys.argv[1]))
