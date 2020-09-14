# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

'''
Examples:

passless -vv -u nobody socks://127.0.0.1:1080/?via=passless://aes-128-cfb:\
PASSWORD@example.com:8080/example.com/passless/&auto_switch=no&\
global_only=no

passless -u nobody http://127.0.0.1:8118/?via=passless://aes-128-cfb:\
PASSWORD@example.com:8080/example.com:8080/passless/&auto_switch=yes&\
global_only=yes
'''

import iofree.contrib.common
import shadowproxy.ciphers
import slowdown.gvars

__version__ = '0.0.1.dev1'

from . import gvars
from . import runtime
from . import utils
from .get_adblk  import get_adblk
from .get_server import get_server
from .proxies.base.server import Context, ProxyBase
from .proxies.passless.shadowsockssocket import ShadowSocksSocket

class Proxy(ProxyBase):

    proto = 'pass'

    def _run(self, socket, client_addr):
        addr_parser = iofree.contrib.common.Addr.get_parser()
        addr        = utils.run_parser(addr_parser, socket)
        target_addr = (addr.host, addr.port)
        via_socket, mode = self.create_connection(target_addr)
        if via_socket is None:
            return Context(None, target_addr, self.proto, mode)
        redundant = addr_parser.readall()
        if redundant:
            via_socket.sendall(redundant)
        return Context(via_socket, target_addr, self.proto, mode)

def handler(rw):
    match     = rw.match
    args      = match.path_section.section.args
    password  = args['password']
    bind_addr = \
        '%s:%s:%s' % (
            match.router_section.name,
            match.  host_section.name,
            match.  path_section.name
        )
    try:
        proxy = proxies[bind_addr]
    except KeyError:
        proxy = get_proxy(bind_addr, password, args)
        proxies[bind_addr] = proxy
    cookie = rw.cookie
    if cookie is None:
        return rw.forbidden()
    morsel = cookie[gvars.token_name]
    if morsel is None:
        return rw.forbidden()
    if not utils.check_token(morsel.value, password):
        return rw.forbidden()
    socket      = ShadowSocksSocket(proxy.kwargs['cipher'], rw)
    client_addr = (rw.environ['REMOTE_ADDR'], rw.environ['REMOTE_PORT'])
    rw.socket.sendall(http_200_head)
    proxy(socket, client_addr)

def get_proxy(bind_addr, password, args):
    cipher = shadowproxy.ciphers.ciphers[args['cipher']](password)
    kwargs = \
        {
               'cipher': cipher,
             'password': password,
            'bind_addr': bind_addr
        }
    if 'via' in args:
        kwargs['via'] = get_server(args['via'], is_via=True)
    proxy = Proxy(**kwargs)
    if 'adblk' in args:
        proxy.adblk = get_adblk(args['adblk'])
    if 'auto_switch' in args:
        auto_switch = args['auto_switch'].lower()
        if   auto_switch in ['y', 'yes', 'on', 'true', 'ok']:
            proxy.auto_switch = True
        elif auto_switch in ['n', 'no', 'off', 'false']:
            proxy.auto_switch = False
        else:
            slowdown.gvars.logger.warning(
                f'ignore unknown auto_switch value {args["auto_switch"]}'
            )
    if 'global_only' in args:
        global_only = args['global_only'].lower()
        if   global_only in ['y', 'yes', 'on', 'true', 'ok']:
            proxy.global_only = True
        elif global_only in ['n', 'no', 'off', 'false']:
            proxy.global_only = False
        else:
            slowdown.gvars.logger.warning(
                f'ignore unknown global_only value {args["global_only"]}'
            )
    return proxy

def initialize(application):
    runtime.application = application

proxies = {}
http_200_head = \
    (
        'HTTP/1.1 200 OK\r\n'
        'Connection: keep-alive\r\n'
        'Content-Encoding: gzip\r\n'
        'Content-Type: video/mp4\r\n'
        'Transfer-Encoding: chunked\r\n'
        'Server: nginx\r\n'
        'Vary: Accept-Encoding\r\n\r\n'
    ).encode('ascii')
