# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

import shadowproxy.protocols.socks5

from ... import utils
from ..base.server import Context, ProxyBase

class SocksProxy(ProxyBase):

    proto = 'socks'

    def _run(self, socket, client_addr):
        socks5_parser = shadowproxy \
                      . protocols   \
                      . socks5      \
                      . server      \
                      . parser(self.auth)
        request = utils.run_parser(socks5_parser, socket)
        addr    = request.addr
        socks5_parser.send_event(0)
        utils.run_parser(socks5_parser, socket)
        target_addr = (addr.host, addr.port)
        via_socket, mode = self.create_connection(target_addr)
        if via_socket is None:
            return Context(None, target_addr, self.proto, mode)
        redundant = socks5_parser.readall()
        if redundant:
            via_socket.sendall(redundant)
        return Context(via_socket, target_addr, self.proto, mode)
