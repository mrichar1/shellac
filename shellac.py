#!/usr/bin/python

from __future__ import print_function
from cmd import Cmd
import readline
import inspect
from functools import wraps


def generator(func):
    @wraps(func)
    def new_func(self, text, state):
        if state == 0:
            self.iterable = iter(func(self, text))
        try:
            return self.iterable.next()
        except StopIteration:
            self.iterable = None
            return None
    return new_func


def completer(func):
    def inner_completer(obj):
        if not hasattr(obj, "completions"):
            obj.completions = []
        obj.completions.append(func)
        return obj
    return inner_completer


def members(obj):
    return (f[0][3:] for f in inspect.getmembers(obj) if f[0].startswith('do_'))


def complete_list(names, token):
    return (x + ' ' for x in names if x.startswith(token))


class Shellac(Cmd, object):

    def __init__(self):
        super(Shellac, self).__init__()
        self.prompt = "(%s) " % (self.__class__.__name__)

    def do_exit(self, args):
        return True

    do_EOF = do_exit

    def do_help(self, args):
        """Help system documentation!"""
        print(self._get_help(args, self) or
              "*** No help for %s" % (args or repr(self)))

    @classmethod
    def _get_help(cls, args, root):
        cmd, _, args = args.partition(' ')
        if not cmd:
            return root.__doc__
        if inspect.isclass(root):
            root = root()
        if hasattr(root, 'do_' + cmd):
            res = cls._get_help(args, getattr(root, 'do_' + cmd))
            if res:
                return res
        try:
            func = getattr(root, 'help_' + cmd)
        except AttributeError:
            if hasattr(root, 'do_' + cmd):
                return getattr(root, 'do_' + cmd).__doc__
            return None
        else:
            return func(args)

    def onecmd(self, line, args='', root=None):
        if not args:
            args = line
        if not root:
            root = self
        if args:
            child, _, args = args.partition(' ')
        elif not line:
            return self.emptyline()
        self.lastcmd = line
        if line == 'EOF':  # http://bugs.python.org/issue13500
            self.lastcmd = ''
        try:
            root = getattr(root, 'do_' + child)
        except AttributeError:
            return self.default(line)
        if inspect.isclass(root):
            # If a class, we must instantiate it
            root = root()
        try:
            # Is root (really) callable
            return root(args)
        # python2 and 3 return different exceptions here
        except (AttributeError, TypeError):
            # It wasn't callable, recurse
            if not args:
                return self.default(line)
            return self.onecmd(line, args, root)

    # traverse_help is recursive so needs to find itself through the class
    @classmethod
    def _traverse_help(cls, tokens, tree):
        if tree is None:
            return []
        elif len(tokens) == 0:
            return members(tree)
        if len(tokens) == 1:
            return complete_list(members(tree), tokens[0])
        elif tokens[0] in members(tree):
            return cls._traverse_help(tokens[1:],
                                      getattr(tree, 'do_' + tokens[0]))
        return []

    # traverse_do is recursive so needs to find itself through the class
    @classmethod
    def _traverse_do(cls, tokens, tree):
        if tree is None:
            return []
        elif len(tokens) == 0:
            return members(tree)
        if len(tokens) == 1:
            if hasattr(tree, 'completions'):
                return (c for f in tree.completions for c in f(tokens[0]))
            return complete_list(members(tree), tokens[0])
        elif tokens[0] in members(tree):
            return cls._traverse_do(tokens[1:],
                                    getattr(tree, 'do_' + tokens[0]))
        return []

    @generator
    def complete(self, text):
        endidx = readline.get_endidx()
        buf = readline.get_line_buffer()
        tokens = buf[:endidx].split()
        if not tokens or buf[endidx - 1] == ' ':
            tokens.append('')
        if tokens[0] == "help":
            return self._traverse_help(tokens[1:], self)
        else:
            return self._traverse_do(tokens, self)
