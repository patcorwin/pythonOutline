'''
Altered version of python standard library pyclbr (python class browser).

Needed to deal with a) nested stuff better and b) know when functions ended.

Known issues: Comments, decorators and strings directly above a def will be
treated as part of the previous def.
'''


import collections
from io import StringIO
import tokenize
from token import NAME, DEDENT, OP


class Class:
    '''Class to represent a Python class.'''
    def __init__(self, module, name, super, file, lineno):
        self.module = module
        self.name = name
        if super is None:
            super = []
        self.super = super
        self.methods = {}
        self.methodends = {}
        self.file = file
        self.lineno = lineno
        self.linenoend = -1

    def _addmethod(self, name, lineno):
        self.methods[name] = lineno
        self.methodends[name] = -1

    def __repr__(self):
        return '<Class s=%i e=%i>' % (self.lineno, self.linenoend)


class Function:
    '''Class to represent a top-level Python function'''
    def __init__(self, module, name, file, lineno):
        self.module = module
        self.name = name
        self.file = file
        self.lineno = lineno
        self.linenoend = -1

    def __repr__(self):
        return '<Func  s=%i e=%i>' % (self.lineno, self.linenoend)


def _readmodule(text):
    _modules = {}
    dict = collections.OrderedDict()
    fullmodule = ''
    fname = ''

    f = StringIO(text)

    stack = [] # stack of (class, indent) pairs

    global prev_def
    global prev_class
    global prev_method

    cur_class = None

    prev_def = None
    prev_class = None
    prev_method = None
    numblanks = 0

    def markend(end):
        end -= 1
        global prev_def
        global prev_class
        global prev_method
        if prev_def:
            prev_def.linenoend = end - numblanks
            prev_def = None
        if prev_class:
            prev_class.linenoend = end - numblanks
            prev_class = None
        if prev_method:
            #prev_method.linenoend = end
            prev_method[0].methodends[prev_method[1]] = end - numblanks
            prev_method = None

    g = tokenize.generate_tokens(f.readline)
    try:
        for tokentype, token, start, _end, _line in g:

            #print(tokentype, token, start[0], _end[0] ) # , '>>' + _line + '<<')
            if tokentype == DEDENT:
                lineno, thisindent = start
                # close nested classes and defs
                while stack and stack[-1][1] >= thisindent:
                    if stack[-1][0]:
                        stack[-1][0].linenoend = lineno
                    del stack[-1]
            elif token == 'def':
                lineno, thisindent = start
                # close previous nested classes and defs
                while stack and stack[-1][1] >= thisindent:
                    if stack[-1][0]:
                        stack[-1][0].linenoend = lineno
                    del stack[-1]
                tokentype, meth_name, start = next(g)[0:3]
                if tokentype != NAME:
                    continue # Syntax error
                if stack:
                    cur_class = stack[-1][0]
                    if isinstance(cur_class, Class):
                        # it's a method
                        cur_class._addmethod(meth_name, lineno)
                        markend(lineno)
                        prev_method = (cur_class, meth_name)
                    # else it's a nested def
                else:
                    # it's a function
                    dict[meth_name] = Function(fullmodule, meth_name, fname, lineno)
                    markend(lineno)
                    if cur_class:
                        cur_class.linenoend = lineno - 1 - numblanks
                        cur_class = None

                    prev_def = dict[meth_name]

                stack.append((None, thisindent)) # Marker for nested fns
            elif token == 'class':
                lineno, thisindent = start
                # close previous nested classes and defs
                while stack and stack[-1][1] >= thisindent:
                    if stack[-1][0]:
                        stack[-1][0].linenoend = lineno
                    del stack[-1]
                tokentype, class_name, start = next(g)[0:3]
                if tokentype != NAME:
                    continue # Syntax error
                # parse what follows the class name
                tokentype, token, start = next(g)[0:3]
                inherit = None
                if token == '(':
                    names = [] # List of superclasses
                    # there's a list of superclasses
                    level = 1
                    super = [] # Tokens making up current superclass
                    while True:
                        tokentype, token, start = next(g)[0:3]
                        if token in (')', ',') and level == 1:
                            n = "".join(super)
                            if n in dict:
                                # we know this super class
                                n = dict[n]
                            else:
                                c = n.split('.')
                                if len(c) > 1:
                                    # super class is of the form
                                    # module.class: look in module for
                                    # class
                                    m = c[-2]
                                    c = c[-1]
                                    if m in _modules:
                                        d = _modules[m]
                                        if c in d:
                                            n = d[c]
                            names.append(n)
                            super = []
                        if token == '(':
                            level += 1
                        elif token == ')':
                            level -= 1
                            if level == 0:
                                break
                        elif token == ',' and level == 1:
                            pass
                        # only use NAME and OP (== dot) tokens for type name
                        elif tokentype in (NAME, OP) and level == 1:
                            super.append(token)
                        # expressions in the base list are not supported
                    inherit = names
                markend(lineno)
                if cur_class:
                    cur_class.linenoend = lineno - 1 - numblanks

                cur_class = Class(fullmodule, class_name, inherit,
                                  fname, lineno)
                prev_class = cur_class
                if not stack:
                    dict[class_name] = cur_class
                stack.append((cur_class, thisindent))

            if tokentype == tokenize.NL:
                numblanks += 1
            elif tokentype in (tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER):
                # Don't let scope trigger clearing numblanks
                pass
            else:
                numblanks = 0
    except StopIteration:
        pass
    markend(_end[0] + 1)  # Cleanup the final entry if there is one, not sure why I need to add one, but I do

    f.close()
    return dict


def prettyprint(results):
    for name, data in results.items():
        if isinstance(data, Class):
            print( name )

            for m in data.methods:
                print( '    ', m, data.methods[m], data.methodends[m])
        else:
            print(name, data.lineno, data.linenoend)


if __name__ == '__main__':
    with open(r'C:\Users\unknowable\AppData\Roaming\Sublime Text 3\Packages\User\classbrowser.py', 'r') as fid:
        res = _readmodule(fid.read())
        prettyprint(res)