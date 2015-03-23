#!/usr/bin/env python

"""
Create a dot file (graphviz) showing modules called from a python script.
For Python 2 code.

USAGE: ./makegraph2.py <mysteriousscript.py> [-D|--maxdepth=<N>]
                                             [--notexaminate=<expr>]
                                             [--ruleout=<expr>]
                                             > outfile.dot
       ./makegraph2.py (-h | --help)

OPTIONS:
  -h --help            Display this help.
  -D --maxdepth <N>    Maximum depth into called modules. Maximum distance
                       that the modules will be from the
                       <mysteriousscript>.
                       [default: 66666]
  --notexaminate=<expr>  Python logical expression. When True for a module
                       {0}, display the module {0} in the graph but do not
                       search for its invoked modules.
                       [default: "False"]
  --ruleout=<expr>     Python logical expression. When True for a module
                       {0}, do not display module {0} at all.
                       [default: "not {0}['path'].startswith(\
"/usr/local/lib/python2.7/dist-packages/pypeline")]

Expression <expr>:

  Special string:  
    "{0}" represents the module evaluated.
    "{0}['name']" is the name of the module.
    "{0}['path']" is its path.
  
  Functions (examples):
    python default logical operators (and, or, not, in, ...)
    other default python functions (str.startwith())
    is_builtin, is_frozen  (from module imp)
  
  Examples:
        #Do not rule out any module / examine all modules
        "False"
        
        #Rule out / do not examine "os" and "sys"
        "{0}['name'] in ['os', 'sys']"

        #Rule out / do not examine builtin or frozen modules
        "is_builtin({0}['name'])" or is_frozen({0}['name'])"

        #Only modules from the package of interest.
        "not {0}['path'].startswith("/usr/local/lib/python2.7/dist-packages/pypeline")
"""

from __future__ import print_function


import re
import sys
import os.path
import argparse
import textwrap
import fileinput

from imp import find_module, is_builtin, is_frozen
from os.path import isdir, isfile


#---------------------------------------------------------------------
#Initialize variables
#---------------------------------------------------------------------
# Number of iterations to check imported modules.
#_maxdepth = 66666  #set to infinite by default.

# Raw string representing the test to be evaluated to rule out a module
# object (stored as a dictionary in the script).
# {0} represents the module object
# Example: ruleout everything that doesn't belong to the paleomix package
#_ruleout = r'not {0}["path"].startswith("/usr/local/lib/python2.7/dist-packages/pypeline")'
# example 2
#_ruleout = r'{0}["name"] in ["os", "sys", "pysam"]'


# Rule for choosing modules to keep but not to examinate:
#_notexaminate = r'is_builtin({0}["name"]) or is_frozen({0}["name"]) or not {0}["path"].startswith("/usr/local")'

#---------------------------------
# Options
#-------------------------

parser = argparse.ArgumentParser(
        formatter_class = argparse.RawDescriptionHelpFormatter,
        usage = "\n\
    %(prog)s <mysteriousscript.py> [-D|--maxdepth=<N>] \n\
                                   [--notexaminate=<expr>] \n\
                                   [--ruleout=<expr>] \n\
                                   > outfile.dot \n\
    %(prog)s (-h | --help)",
        description = "Create a dot file (graphviz) showing modules \
called from a python script. For Python 2 code.",
        epilog = textwrap.dedent('''\
            Expression <expr>:

              Special string:  
                "{0}" represents the module evaluated.
                "{0}['name']" is the name of the module.
                "{0}['path']" is its path.
              
              Functions (examples):
                python default logical operators (and, or, not, in, ...)
                other default python functions (str.startwith())
                is_builtin, is_frozen  (from module imp)
              
              Examples:
                #Do not rule out any module / examine all modules
                "False"
                
                #Rule out / do not examine "os" and "sys"
                "{0}['name'] in ['os', 'sys']"

                #Rule out / do not examine builtin or frozen modules
                "is_builtin({0}['name'])" or is_frozen({0}['name'])"

                #Only modules from the package of interest [--ruleout default]
                "not {0}['path'].startswith("/usr/local/lib/python2.7/dist-packages/pypeline")''')) 

parser.add_argument('script', type=str, metavar='<mysteriousscript.py>')
parser.add_argument('-D', '--maxdepth', metavar='<N>', type=int,
        default=66666, 
        help="Maximum depth into called modules, i.e. maximum distance \
                that the modules will be from the <mysteriousscript.py>\
                [default: 66666]")
parser.add_argument('--notexaminate', type=str, metavar='<expr>', 
        default="False",
        help="Python logical expression. When True for a module {0}, \
                display the module {0} in the graph but do not search \
                for its invoked modules. [default: \"False\"]")
parser.add_argument('--ruleout', type=str, metavar='<expr>',
        default="not {0}['name'].startswith(\"pypeline\")",
        help="Python logical expression. When True for a module {0}, do \
            not display module {0} at all. --ruleout will override \
            --notexaminate. By default keep only modules from paleomix.")
args = parser.parse_args()

#for (k,v) in vars(args).iteritems():
#    print(k + " : " + str(v) , sys.stderr)
#print(vars(args))
#print(args)
#sys.exit()

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
    if isdir(filename):
    #    print("In importedModule:\n\t" + filename +
    #           " : filename is a directory", file=sys.stderr)
        filename = os.path.join(filename, "__init__.py")
        #print("in usedFunctions():\nTrying with: " + filename,
        #        file=sys.stderr)
        if not isfile(filename):
           # print("---usedFunctions---: " + filename + " is not a file.",
           #         file=sys.stderr)
            return []
    #print("---usedFunctions--> Opening " + filename, file=sys.stderr)
    with open(filename) as FILE:
        filetext = FILE.read()
        #remove commented lines
        text = re.sub(r'^\s*#.*$', '', filetext, flags=re.MULTILINE)
        if "importedFct" in module.keys():
            usedFct = set(module["importedFct"])
        elif "as" in module.keys():
            usedFct = re.findall(r'(?<=%s\.)[\w\.]+\(?' % module["as"],
                    filetext)
        else:
            usedFct = re.findall(r'(?<=%s\.)[\w\.]+\(?' % module["name"],
                    filetext)
    return set(usedFct)


def findModule(modulename, abbrv = None, importedFct = None):
    """find path to module.
    Return a dictionary describing the module.
    This function has to be rewritten (is_builtin test, type key)."""
    modules = modulename.split(".")
    path = sys.path
    for m in modules:
        try:
            p = find_module(m, path)
            path.append(p[1])
            #print("adding path %s to path list" % p)
            #print("path list = %s" %path)
        except ImportError:
            return {"name": modulename,
                    "NotExaminate":"Not Found (ImportError)",
                    "path":"Not Found (ImportError)"}
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
    if eval(args.notexaminate.format("module")):
        module["NotExaminate"] = 1
    return module


def importedModules(filename):
    """Return imported modules in a python script"""
    print("   ---importedModules---", file = sys.stderr)
    modules = []
    allmodulenames = []
    if isdir(filename):
        #print("In importedModule:\n" + filename +
        #        " : filename is a directory", file=sys.stderr)
        filename = os.path.join(filename, "__init__.py")
        #print("Trying with: " + filename, file=sys.stderr)
        if not isfile(filename):
        #    print(filename + " is not a file.", file=sys.stderr)
            return []
    print("   --> Opening " + filename, file=sys.stderr)
    with open(filename) as FILE:
        text = FILE.read()
        # only catch module name:
        m_import = re.findall(r'^\s*import (\S+)(?=\s*$)', text,
                re.MULTILINE)
        m_importas = re.findall(r'^\s*import (\S+) as (\S+)$', text,
                re.MULTILINE)
        # "from ... import" written in one line: 
        m_fromimport = re.findall(
                r'(^\s*from \S+ import \w+(?:\s*,\s*)?(?:\w+(?:\s*,\s*)?)*)',
                text, re.MULTILINE)
        # "from ... import" spanning multiple lines:
        m_fromimport += re.findall(
                r'(^\s*from \S+ import \s*\\\n(?:\s*\w+,\s*\\\n)*\s*\w+\s*)',
                text, re.MULTILINE)
        if m_import:
            modulenames = list(set(m_import))  #remove duplicates
            allmodulenames += modulenames
            newmodules = [findModule(n) for n in modulenames]
            modules += [new for new in newmodules \
                    if not eval(args.ruleout.format("new"))]
        if m_importas:
            modulenames = [m[0] for m in m_importas]
            allmodulenames += modulenames
            abbrv = [m[1] for m in m_importas]
            newmodules = [findModule(modulenames[i], abbrv=abbrv[i]) for \
                    i in range(len(modulenames))]
            modules += [new for new in newmodules \
                    if not eval(args.ruleout.format("new"))]
        if m_fromimport:
            modulenames = [re.search(r'(?<=from )\S+', m).group(0) for \
                    m in m_fromimport]
            modulenames = list(set(modulenames))  #remove duplicates
            allmodulenames += modulenames
            importedFct = [re.findall(r'[\w.]+', m)[3:] for m in \
                    m_fromimport]
            newmodules = [findModule(modulenames[i],
                                    importedFct = importedFct[i]) \
                        for i in range(len(modulenames))]
            modules += [new for new in newmodules \
                    if not eval(args.ruleout.format("new"))]
    # print some info
    #print("""    Nb of modules found: %s   Not Ignored: %s
    #Modules Not Ignored: %s""" % (len(allmodulenames), len(modules),
    #        "  ".join([mod["name"] for mod in modules])),
    #    file = sys.stderr)
    return modules


def DoRound(LevelLength, untested, tested):
    """Find Modules called by the modules of the previous level.
    Print the new edges in the graphviz dot format. 
    Return the number of Modules in the next level, untested (updated)
    and tested (updated)"""

    nextLevelLength = 0
    
    for k in range(LevelLength):
        fromfile = untested[0]
        print("   module %s\n   k = %s   untested = %s\ntested = %s" % \
                (fromfile["name"], k,
                    "  ".join([mod["name"] for mod in untested]),
                    "  ".join(tested)),
            file = sys.stderr)
        
        #Do not examinate some types of modules
        if fromfile.get("NotExaminate"):
            pass
            #print("---DoRound---: Not exploring %s module %s" \
            #       % (fromfile["type"],
            #    fromfile["name"]), file=sys.stderr)
        else:
            newmodules = importedModules(fromfile["path"])
            try:
                for new in newmodules:
                    usedFct = usedFunctions(fromfile["path"], new)
                    #reshape string not to exceed fixed width
                    usedFct_str = join_fixedwidth(usedFct)
                    print("\"%s\" -> \"%s\" [label=\"%s\"]" %(
                        fromfile["name"], new["name"], usedFct_str))
                    if new["name"] not in [u["name"] for u in 
                            untested] + tested:
                        untested.append(new)
                        nextLevelLength += 1
                        print("   nextLevelLength += 1 -> %s (%s)" % \
                                (nextLevelLength, new["name"]),
                                file=sys.stderr)
            except IOError as e:
                print(e, file=sys.stderr)
                print("problem in module: %s" %fromfile,
                        file=sys.stderr)
                #print("Wrong file was %s" % (fromfile["path"]),
                #        file=sys.stderr)
                #for fct in fromfile["usedFct"]:
            except KeyError as e:
                print(e, file=sys.stderr)
                print("Dictionary doesnt contain required keys:\
                        \"path\" and \"name\".\n %s" % fromfile,
                        file=sys.stderr)
        tested.append(fromfile["name"])
        try:
            untested = untested[1:]
        except IndexError as e: #I dont even know if this error can occur
            print(e, file=sys.stderr)
            return nextLevelLength
    return nextLevelLength, untested, tested


def main(args):
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
            """ % os.path.basename(args.script))
    i  = 0   #iteration number. Number of levels checked.
    
    untested = [ {"name": os.path.basename(args.script),
                 "path": args.script} ]
    tested = []

    LevelLength = len(untested)
    while (len(untested) > 0) and (i <= args.maxdepth):
        print ("***** Round i=%s (max: %s) ***** LevelLength = %s" % \
                (i, args.maxdepth, LevelLength),
                file=sys.stderr)
        #this function updates untested, tested.
        LevelLength, \
        untested, \
        tested = DoRound(LevelLength, untested, tested)
        i += 1
    print("\n}\n")


main(args)
#if __name__ == '__main__':
#    sys.exit(main(args))

#print(importedModules(sys.argv[1]))
