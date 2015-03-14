#!/usr/bin/env python

"""
Create a dot file (graphviz)  showing modules called by a python script.
For Python 2 code
USE: ./makegraph.py mysteriousscript.py
"""

from __future__ import print_function

import re
import sys
import os.path
import fileinput


from imp import find_module, is_builtin, is_frozen
from os.path import isdir, isfile

#deprecated but works.
#from importlib import import_module #not deprecated but f*** doesn't work
#from modulefinder import ModuleFinder

#import pypeline.tools

#from matplotlib.pyplot import plot, \
#        show, \
#        subplot


#---------------------------------------------------------------------
#Initialize variables
#---------------------------------------------------------------------
ignore = ["os", "sys"] # to avoid displaying these very well known ones
#ignore += ["pysam"] #because too complex

#---------------------------------------------------------------------
#functions
#---------------------------------------------------------------------

def join_fixedwidth(stringlist, joinstr = ",", maxwidth=50):
    stringlist = list(stringlist)
    if not stringlist:
        return ''
    elif len(stringlist) == 1:
        return stringlist[0]
    else:
        s = stringlist[0]
        i = len(s)
        for e in stringlist[1:]:
            i += len(e)
            if i // maxwidth == 0:
                s += joinstr + e
                i += 1 #for the comma
            else:
                s += ",\\n" + e + joinstr
                i = len(e) + 1
        return s


def usedFunctions(filename, module):
    """find functions from a module.
    'module' is a list of dictionaries like returned by
    'importedModules':."""
    with open(filename) as FILE:
        filetext = FILE.read()
        #remove commented lines
        text = re.sub(r'^\s*#.*$', '', filetext, flags=re.MULTILINE)
        if "importedFct" in module.keys():
            usedFct = set(module["importedFct"])
        elif "as" in module.keys():
            usedFct = re.findall(r'(?<=%s\.)\w+\(?' % module["as"], filetext)
        else:
            usedFct = re.findall(r'(?<=%s\.)\w+\(?' % module["name"], filetext)
    return set(usedFct)


def importedModules(filename):
    """Return imported modules in a python script"""
    modules = []
    if isdir(filename):
        print("In importedModule:\n\t" + filename +
                " : filename is a directory", file=sys.stderr)
        filename = os.path.join(filename, "__init__.py")
        print("Trying with:\n\t" + filename, file=sys.stderr)
        if not isfile(filename):
            print(filename + " is not a file.", file=sys.stderr)
            return []
    print("--> Opening " + filename, file=sys.stderr)
    with open(filename) as FILE:
        text = FILE.read()
        m_import = re.findall(r'^\s*import \S+\b(?! as )', text,
                re.MULTILINE)
        m_importas = re.findall(r'^\s*import \S+ as \S+$', text,
                re.MULTILINE)
        m_fromimport = re.findall(
                r'^\s*from \S+ import (?:[\s\\\n]*[\w,]+)*[^,]$', text,
                re.MULTILINE)
        if m_import:
            modulenames = [re.search("\S+$", m).group(0) for \
                    m in m_import]
            modulenames = [mod for mod in modulenames if mod not in ignore]
            modules += [findModule(mod) for mod in \
                    modulenames]
        if m_importas:
            modulenames = [re.search('(?<=import )\S+', m).group(0) \
                    for m in m_importas]
            modulenames = [mod for mod in modulenames if mod not in ignore]
            abbrv = [re.search('(?<= as )\S+', m).group(0) for m in \
                    m_importas]
            modules += [findModule(modulenames[i], abbrv=abbrv[i]) for i \
                    in range(len(modulenames))]
        if m_fromimport:
            modulenames = [re.search(r'(?<=from )\S+', m).group(0) for \
                    m in m_fromimport]
            modulenames = [mod for mod in modulenames if mod not in ignore]
            importedFct = [re.findall(r'[\w.]+', m)[3:] for m in \
                    m_fromimport]
            modules += [findModule(modulenames[i],
                importedFct = importedFct[i]) for i in \
                        range(len(modulenames))]
    return modules




def findModule(modulename, abbrv = None, importedFct = None):
    """prints path to module"""
    modules = modulename.split(".")
    path = sys.path
    for m in modules:
        if is_builtin(m):
            module = {"name": modulename, "type": "Builtin"}
            break
        elif is_frozen(m):
            module = {"name": modulename, "type": "Frozen"}
            break
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
            module = {"name": modulename,
                "type": type,
                "file": p[0],
                "path": p[1],
                "details": p[2]} #p is a tuple:
                                #(file, filename, (suffixe, mode, type))
                                #exemple from "os":
            #(<open file '/usr/lib/python2.7/os.py' mode 'U' at 0x7f..>,
                                #'/usr/lib/python2.7/os.py',
                                #('.py', 'U', 1))
    if abbrv:
        module["as"] = abbrv
    if importedFct:
        module["importedFct"] = importedFct
    return module


def main(_argv):
    """write links between modules in a .dot file"""
    print("""digraph \"%s\" {
        graph [
            rankdir=LR
            pad="0,0"
            //fillcolor = ...
            //color = "transparent"
        ]
        node [
            shape = box
            style = "rounded"
            //fillcolor = rosybrown //pink4
            //fontcolor = "black"
        ]
        edge [fontsize = 8]
            """ % _argv)
    untested = importedModules(_argv)
    tested = []
    for mod in untested:
        if mod not in tested:
            usedFct = usedFunctions(_argv, mod)
            print ("\"%s\" -> \"%s\" [label = \"%s\"]" %(_argv, mod["name"],
                join_fixedwidth(usedFct)))
    while len(untested) > 0:
        fromfile = untested[0]
        if fromfile["type"] in ["Builtin", "Frozen", "Installed",
                                            "Not Found (ImportError)"]:
            print("Ignoring %s module %s" % (fromfile["type"],
                fromfile["name"]), file=sys.stderr)
        else:
            try:
                newmodules = importedModules(fromfile["path"])
                for new in newmodules:
                    usedFct = usedFunctions(fromfile["path"], new)
                    #reshape usedFct so that it doesnt exceed a fixed width
                    usedFct_str = join_fixedwidth(usedFct)
                    print("\"%s\" -> \"%s\" [label=\"%s\"]" %(
                        fromfile["name"], new["name"], usedFct_str))
                    if new not in untested+tested:
                        untested.append(new)
            except IOError as e:
                print(e, file=sys.stderr)
                print("problem in module: %s" %fromfile, file=sys.stderr)
                #print("Wrong file was %s" % (fromfile["path"]),
                #        file=sys.stderr)
                #for fct in fromfile["usedFct"]:
            except KeyError as e:
                print(e, file=sys.stderr)
                print("Dictionary is: %s" %fromfile, file=sys.stderr)
        tested.append(fromfile)
        untested = untested[1:]
    print("\n}\n")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("""Error: Please provide an argument to the script.
Description:
    Create a dot file (graphviz)  showing called modules by a python script. For Python2 code.
USE: ./makegraph.py mysteriousscript.py
""")
    else:
        sys.exit(main(sys.argv[1]))

#print(importedModules(sys.argv[1]))
