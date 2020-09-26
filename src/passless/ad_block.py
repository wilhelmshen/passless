# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

import argparse
import os.path
import weakref

from . import runtime

DIRECT = 0
PROXY  = 1
REJECT = 2

def ADBLKArgument(filename):
    app = getattr(runtime, 'application', None)
    if app is None:
        os_path = os.path
    else:
        os_path = app.fs.os.path
    path = os_path.abspath(filename)
    if os_path.isfile(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f'No such file: {filename}')

def get_adblk(path):
    if path in adblks:
        return adblks[path]
    adblks[path] = adblk = AdBlock(path)
    return adblk

class AdBlock(object):

    def __init__(self, path):
        app = getattr(runtime, 'application', None)
        if app is None:
            file =        open(path, 'rb')
        else:
            file = app.fs.open(path, 'rb')
        try:
            data = file.read()
        finally:
            file.close()
        self.root = {}
        for line in data.decode().splitlines():
            try:
                revdomain, mode = line.split(None, 1)
            except (IndexError, ValueError):
                continue
            node = self.root
            for name in revdomain.split('.'):
                node = node.setdefault(name, {})
            try:
                node[None] = modes[mode.upper()]
            except KeyError:
                continue

    def __call__(self, domain, default=DIRECT, strict_mode=False):
        node = self.root
        if strict_mode:
            for name in reversed(domain.split('.')):
                next_ = node.get(name)
                if next_ is None:
                    return node.get(None, default)
                else:
                    node = next_
            else:
                return node.get(None, default)
        else:
            for name in reversed(domain.split('.')):
                next_ = node.get(name)
                if next_ is None:
                    return node.get(None, default)
                else:
                    mode = next_.get(None)
                    if mode is None:
                        node = next_
                    else:
                        return mode
            else:
                return default

modes  = {'DIRECT': DIRECT, 'PROXY': PROXY, 'REJECT': REJECT}
adblks = weakref.WeakValueDictionary()
