# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

import errno
import shadowproxy.proxies.shadowsocks.parser

from ... import gvars

class ShadowSocksSocket(object):

    def __init__(self, cipher, rw):
        self.ss_parser = shadowproxy \
                       . proxies     \
                       . shadowsocks \
                       . parser      \
                       . ss_reader   \
                       . parser(cipher)
        self.cipher    = cipher
        self.rw        = rw
        self.encrypt   = None

    def __enter__(self):
        return self

    def __exit__(self, et, e, tb):
        if self.rw is not None:
            self.rw.close()
            self.rw = None

    @property
    def closed(self):
        return self.rw is None

    def sendall(self, data):
        if self.rw is None:
            raise BrokenPipeError(errno.EPIPE, 'Broken pipe')
        if self.encrypt is None:
            iv, self.encrypt = self.cipher.make_encrypter()
            to_send = iv + self.encrypt(data)
        else:
            to_send = self.encrypt(data)
        self.rw.socket.sendall(b'%x\r\n%s\r\n' % (len(to_send), to_send))

    def recv(self, size=gvars.PACKET_SIZE):
        if self.rw is None:
            return b''
        data = self.rw.reader.readline(6)
        if not data:
            return b''
        assert LF == data[-1]
        size = int(data, 16)
        if 0 == size:
            return b''
        else:
            data = self.rw.reader.read(size)
            if not data:
                return b''
        lf = self.rw.reader.readline(2)
        assert lf in (b'\n', b'\r\n')
        self.ss_parser.send(data)
        return self.ss_parser.read_output_bytes()

    def close(self):
        if self.rw is not None:
            self.rw.socket.close()
            self.rw = None

LF = ord(b'\n')
