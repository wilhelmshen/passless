# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

import errno
import os.path
import weakref

from . import runtime

DIRECT = 0
PROXY  = 1
REJECT = 2

def get_adblk(filename):
    app = runtime.application
    fs  = app.fs
    if filename.startswith(os.path.sep):
        adblk = get_adblk_by_abspath(filename)
        if adblk is None:
            raise FileNotFoundError(errno.ENOENT,
                                    f'No such file: {filename}')
        else:
            return adblk
    adblk = \
        get_adblk_by_abspath(
            fs.os.path.abspath(
                os.path.join(app.opts.home, filename)
            )
        )
    if adblk is not None:
        return adblk
    adblk = \
        get_adblk_by_abspath(
            fs.os.path.abspath(
                os.path.join(
                    app.opts.home,
                    'etc',
                    filename
                )
            )
        )
    if adblk is not None:
        return adblk
    adblk = get_adblk_by_abspath(fs.os.path.abspath(filename))
    if adblk is None:
        raise FileNotFoundError(errno.ENOENT,
                                f'No such file: {filename}')
    else:
        return adblk

def get_adblk_by_abspath(path):
    adblk = adblks.get(path)
    if adblk is None:
        fs = runtime.application.fs
        if fs.os.path.isfile(path):
            adblks[path] = adblk = AdBlock(fs, path)
            return adblk
        else:
            return None
    else:
        return adblk

class AdBlock(object):

    def __init__(self, fs, path):
        file = fs.open(path, 'rb')
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
