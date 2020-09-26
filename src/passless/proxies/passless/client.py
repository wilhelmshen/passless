# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

import errno
import gevent.socket
import slowdown.http

from ... import gvars
from ... import utils
from . import ImNotSpider
from .shadowsockssocket import ShadowSocksSocket

class PasslessClient(object):

    proto = 'pass'

    def __init__(self, bind_addr, cipher, host, path, password, **kwargs):
        self.bind_addr = bind_addr
        self.cipher    = cipher
        self.host      = host
        self.path      = path
        self.password  = password
        self.kwargs    = kwargs

    def create_connection(self, target_addr):
        socket = gevent.socket.create_connection(self.bind_addr)
        reader = socket.makefile(mode='rb')
        socket.sendall(
            (
                f'GET {self.path}{gvars.gen_filename()} HTTP/1.1\r\n'
                f'Host: {self.host}\r\n'
                f'User-Agent: {ins.random()}\r\n'
                f'Accept: {gvars.accept}\r\n'
                f'Cookie: {gvars.token_name}='
                        f'{utils.make_token(self.password)}\r\n'
                f'Content-Type: {gvars.content_type}\r\n'
                'Transfer-Encoding: chunked\r\n'
                f'Accept-Language: {gvars.accept_language}\r\n'
                'Accept-Encoding: gzip, deflate\r\n'
                'DNT: 1\r\n'
                'Connection: keep-alive\r\n\r\n'
            ).encode()
        )
        environ = slowdown.http.new_environ(reader, server_side=False)
        if '200' != environ['RESPONSE_STATUS']:
            raise BrokenPipeError(errno.EPIPE, 'Authentication failed')
        rw = SSRWPair(socket, reader, environ)
        via_socket = ShadowSocksSocket(self.cipher, rw)
        via_socket.sendall(utils.pack_addr(target_addr))
        return via_socket

class SSRWPair(object):

    def __init__(self, socket, reader, environ):
        self.socket  = socket
        self.reader  = reader
        self.environ = environ

ins = ImNotSpider.ImNotSpider()
