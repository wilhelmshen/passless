# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

import errno
import gevent
import gevent.socket
import slowdown.gvars
import slowdown.logging

from ... import gvars
from ... import utils
from ...get_adblk import DIRECT, PROXY, REJECT

class ProxyBase(object):

    proto = 'proxy'

    def __init__(self, **kwargs):
        self.adblk       = kwargs.get('adblk')
        self.auth        = kwargs.get('auth')
        self.bind_addr   = kwargs.get('bind_addr')
        self.plugin      = kwargs.get('plugin')
        self.via         = kwargs.get('via')
        self.kwargs      = kwargs
        if 'auto_switch' in kwargs:
            self.auto_switch = kwargs['auto_switch']
        else:
            self.auto_switch = gvars.default_auto_switch
        if 'global_only' in kwargs:
            self.global_only = kwargs['global_only']
        else:
            self.global_only = gvars.default_global_only

    def __call__(self, socket, addr):
        try:
            ctx = self._run(socket, addr)
        except Exception as err:
            if isinstance(self.bind_addr, str):
                bind_addr = self.bind_addr
            else:
                bind_addr = "%s:%d" % self.bind_addr
            if   slowdown.gvars.logger.level <= slowdown.logging.DEBUG:
                slowdown.gvars.logger.debug(utils.exc())
            elif slowdown.gvars.logger.level <= slowdown.logging.INFO:
                slowdown.gvars.logger.info(
                    f'{"%s:%d" % addr} - '
                    f'\033[32m{self.proto}://\033[0m{bind_addr} - '
                    f'\033[33m{err}\033[0m'
                )
            return
        if ctx.via_socket is None:
            if slowdown.gvars.logger.level <= slowdown.logging.INFO:
                if isinstance(self.bind_addr, str):
                    bind_addr = self.bind_addr
                else:
                    bind_addr = "%s:%d" % self.bind_addr
                if REJECT == ctx.mode:
                    slowdown.gvars.logger.info(
                        f'{"%s:%d" % addr} - '
                        f'\033[32m{ctx.proto}://\033[0m{bind_addr} - '
                        '\033[31mADBLK\033[0m - '
                        f'{"%s:%d" % ctx.target_addr}'
                    )
                else:
                    slowdown.gvars.logger.info(
                        f'{"%s:%d" % addr} - '
                        f'\033[32m{ctx.proto}://\033[0m{bind_addr} - '
                        f'\033[35mPERFORMED\033[0m'
                    )
            return
        if slowdown.gvars.logger.level <= slowdown.logging.INFO:
            if isinstance(self.bind_addr, str):
                bind_addr = self.bind_addr
            else:
                bind_addr = "%s:%d" % self.bind_addr
            if   DIRECT == ctx.mode:
                slowdown.gvars.logger.info(
                    f'{"%s:%d" % addr} - '
                    f'\033[32m{ctx.proto}://\033[0m{bind_addr} - '
                    f'{"%s:%d" % ctx.target_addr}'
                )
            elif PROXY  == ctx.mode:
                slowdown.gvars.logger.info(
                    f'{"%s:%d" % addr} - '
                    f'\033[32m{ctx.proto}://\033[0m{bind_addr} - '
                    f'\033[32m{self.via.proto}://\033[0m'
                    f'{"%s:%d" % self.via.bind_addr} - '
                    f'{"%s:%d" % ctx.target_addr}'
                )
            else:
                slowdown.gvars.logger.info(
                    f'{"%s:%d" % addr} - '
                    f'\033[32m{ctx.proto}://\033[0m{bind_addr} - '
                    f'\033[31mLIMBO-{ctx.mode}\033[0m - '
                    f'{"%s:%d" % ctx.target_addr}'
                )
        reverse_relay_task = \
            gevent.spawn(
                reverse_relay,
                gevent.getcurrent(),
                socket,
                ctx.via_socket
            )
        while True:
            try:
                data = socket.recv(gvars.PACKET_SIZE)
            except gevent.GreenletExit:
                break
            except:
                reverse_relay_task.kill(block=False)
                if slowdown.gvars.logger.level <= slowdown.logging.DEBUG:
                    slowdown.gvars.logger.debug(utils.exc())
                break
            if not data:
                reverse_relay_task.kill(block=False)
                break
            if ctx.via_socket.closed:
                return
            try:
                ctx.via_socket.sendall(data)
            except gevent.GreenletExit:
                break
            except:
                reverse_relay_task.kill(block=False)
                if slowdown.gvars.logger.level <= slowdown.logging.DEBUG:
                    slowdown.gvars.logger.debug(utils.exc())
                break

    def create_connection(self, target_addr):
        if self.global_only and not utils.is_global(target_addr[0]):
            raise ValueError('non global target address is forbidden '
                             f'{target_addr}')
        source_addr = self.kwargs.get('source_addr')
        if self.adblk is None:
            if self.via is None:
                return \
                    (
                        gevent.socket.create_connection(target_addr),
                        DIRECT
                    )
            elif self.auto_switch:
                res = None
                try:
                    with gevent.Timeout(gvars.auto_switch_timeout, False):
                        res = \
                            (
                                gevent.socket.create_connection(
                                    target_addr
                                ),
                                DIRECT
                            )
                except:
                    if slowdown.gvars.logger.level <= \
                       slowdown.logging.DEBUG:
                        slowdown.gvars.logger.debug(utils.exc())
                if res is None:
                    return \
                        (
                            self.via.create_connection(target_addr),
                            PROXY
                        )
                else:
                    return res
            else:
                return \
                    (
                        self.via.create_connection(target_addr),
                        PROXY
                    )
        result = self.adblk(target_addr[0])
        if   result == REJECT:
            return (None, REJECT)
        elif result == PROXY:
            if self.via is None:
                return \
                    (
                        gevent.socket.create_connection(target_addr),
                        DIRECT
                    )
            else:
                return \
                    (
                        self.via.create_connection(target_addr),
                        PROXY
                    )
        else:
            if self.via is None or not self.auto_switch:
                return \
                    (
                        gevent.socket.create_connection(target_addr),
                        DIRECT
                    )
            else:
                res = None
                try:
                    with gevent.Timeout(gvars.auto_switch_timeout, False):
                        res = \
                            (
                                gevent.socket.create_connection(
                                    target_addr
                                ),
                                DIRECT
                            )
                except:
                    if slowdown.gvars.logger.level <= \
                       slowdown.logging.DEBUG:
                        slowdown.gvars.logger.debug(utils.exc())
                if res is None:
                    return \
                        (
                            self.via.create_connection(target_addr),
                            PROXY
                        )
                else:
                    return res

def reverse_relay(relay_task, socket, via_socket):
    while True:
        try:
            data = via_socket.recv(gvars.PACKET_SIZE)
        except gevent.GreenletExit:
            break
        except:
            relay_task.kill(block=False)
            if slowdown.gvars.logger.level <= slowdown.logging.DEBUG:
                slowdown.gvars.logger.debug(utils.exc())
            break
        if not data:
            relay_task.kill(block=False)
            break
        if socket.closed:
            return
        try:
            socket.sendall(data)
        except gevent.GreenletExit:
            break
        except:
            relay_task.kill(block=False)
            if slowdown.gvars.logger.level <= slowdown.logging.DEBUG:
                slowdown.gvars.logger.debug(utils.exc())
            break

class Context(object):

    __slots__ = ['mode', 'proto', 'target_addr', 'via_socket']

    def __init__(self, via_socket=None, target_addr=None, proto=None,
                 mode=None):
        self.via_socket  =  via_socket
        self.target_addr = target_addr
        self.proto       = proto
        self.mode        = mode
