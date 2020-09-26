# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

'''
Examples:

passless -vv -u nobody socks://127.0.0.1:1080/?via=passless://aes-128-cfb:\
PASSWORD@example.com:8080/example.com/passless/&autoswitch=no&\
globalonly=no

passless -u nobody http://127.0.0.1:8118/?via=passless://aes-128-cfb:\
PASSWORD@example.com:8080/example.com:8080/passless/&autoswitch=yes&\
globalonly=yes
'''

import iofree.contrib.common
import shadowproxy.ciphers
import slowdown.gvars

__version__ = '0.0.1.dev1'

from . import gvars
from . import runtime
from . import utils
from .ad_block import get_adblk, ADBLKArgument
from .server   import get_client, URIArgument
from .proxies.base.server import Context, ProxyBase
from .proxies.passless.shadowsockssocket import ShadowSocksSocket

def initialize(application):
    runtime.application = application

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
        uri = URIArgument(args['via'], is_via=True)
        kwargs['via'] = get_client(uri)
    proxy = Proxy(**kwargs)
    if 'adblk' in args:
        path = ADBLKArgument(args['adblk'])
        proxy.adblk = get_adblk(path)
    if 'autoswitch' in args:
        autoswitch = args['autoswitch'].lower()
        if   autoswitch in gvars.yes:
            proxy.autoswitch = True
        elif autoswitch in gvars.no:
            proxy.autoswitch = False
        else:
            proxy.autoswitch = gvars.default_autoswitch
            if autoswitch != '':
                slowdown.gvars.logger.warning(
                    f'ignore unknown autoswitch value {args["autoswitch"]}'
                )
    if 'globalonly' in args:
        globalonly = args['globalonly'].lower()
        if   globalonly in gvars.yes:
            proxy.globalonly = True
        elif globalonly in gvars.no:
            proxy.globalonly = False
        else:
            proxy.globalonly = gvars.default_globalonly
            if globalonly != '':
                slowdown.gvars.logger.warning(
                    f'ignore unknown globalonly value {args["globalonly"]}'
                )
    return proxy

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
