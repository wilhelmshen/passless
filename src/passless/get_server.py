# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

import base64
import collections
import gevent.server
import gevent.socket
import ipaddress
import re
import shadowproxy.ciphers
import slowdown.gvars
import urllib.parse

from . import proxies
from .get_adblk import get_adblk

default_port  = 0
default_ports = \
    {
           'http': 80,
          'https': 443,
          'socks': 8527,
        'forward': 80,
            'red': 12345
    }

def get_server(uri, is_via=False):
    if regex_scheme.search(uri) is None:
        if is_via:
            url = urllib.parse.urlparse('passless://' + uri)
        else:
            url = urllib.parse.urlparse('socks://' + uri)
    else:
        url = urllib.parse.urlparse(uri)
    kwargs = {}
    if is_via:
        proto = proxies.   via_protos[url.scheme]
    else:
        proto = proxies.server_protos[url.scheme]
    userinfo, _, loc = url.netloc.rpartition('@')
    if userinfo:
        if ':' not in userinfo:
            userinfo = base64.b64decode(userinfo).decode('ascii')
        try:
            cipher_name, _, password = userinfo.partition(':')
        except IndexError:
            raise ValueError('invalid user: ' + userinfo)
        if url.scheme.startswith('ss') or \
           url.scheme in ['pass', 'passless']:
            kwargs['cipher'] = shadowproxy \
                             . ciphers     \
                             . ciphers[cipher_name](password)
            if not kwargs['cipher'].is_stream_cipher:
                if is_via:
                    proto = proxies.   via_protos['aead']
                else:
                    proto = proxies.server_protos['aead']
        elif url.scheme in ['http', 'https', 'socks', 'forward']:
            kwargs['auth'] = (cipher_name.encode(), password.encode())
    elif url.scheme in ['pass', 'passless', 'ss', 'ssudp']:
        raise ValueError('you need to assign cryto algorithm and '
                         f'password ({uri}), {via_example}')
    host, port = parse_addr(loc)
    if port == -1:
        port = default_ports.get(url.scheme, default_port)
    bind_addr = (str(host), port)
    kwargs['bind_addr'] = bind_addr
    if url.scheme in ['pass', 'passless']:
        host, sep, path = url.path.lstrip('/').partition('/')
        if host:
            kwargs['host'] = host
        else:
            kwargs['host'] = loc
        if path.startswith('/'):
            kwargs['path'] = path
        else:
            kwargs['path'] = '/' + path
        kwargs['password'] = password
    elif url.path not in ['', '/']:
        kwargs['path'] = url.path
    qs = urllib.parse.parse_qs(url.query)
    if url.scheme == 'tunneludp':
        if 'target' not in qs:
            raise ValueError('destitation must be assign in tunnel udp '
                             'mode, example tunneludp://:53/?target='
                             '8.8.8.8:53')
        host, port = parse_addr(qs['target'][0])
        kwargs['target_addr'] = (str(host), port)
    if is_via:
        return proto(**kwargs)
    elif 'via' in qs:
        kwargs[ 'via' ] = get_server(qs[ 'via' ][0], True)
    if 'adblk' in qs:
        kwargs['adblk'] = get_adblk (qs['adblk'][0])
    if 'auto_switch' in qs:
        auto_switch = qs['auto_switch'][0].lower()
        if   auto_switch in ['', 'y', 'yes', 'on', 'true', 'ok']:
            kwargs['auto_switch'] = True
        elif auto_switch in ['n', 'no', 'off', 'false']:
            kwargs['auto_switch'] = False
        else:
            slowdown.gvars.logger.warning(
                f'ignore unknown auto_switch value {qs["auto_switch"][0]}'
            )
    if 'global_only' in qs:
        global_only = qs['global_only'][0].lower()
        if   global_only in ['', 'y', 'yes', 'on', 'true', 'ok']:
            kwargs['global_only'] = True
        elif global_only in ['n', 'no', 'off', 'false']:
            kwargs['global_only'] = False
        else:
            slowdown.gvars.logger.warning(
                f'ignore unknown global_only value {qs["global_only"][0]}'
            )
    if ':' in bind_addr[0]:
        family = gevent.socket.AF_INET6
    else:
        family = gevent.socket.AF_INET
    if url.scheme.endswith('udp'):
        raise NotImplementedError('udp is currently not supported')
    else:
        if url.scheme in ['https']:
            if not url.fragment:
                raise ValueError('#keyfile,certfile is needed')
            try:
                keyfile, sep, certfile = url.fragment.partition(',')
            except (IndexError, ValueError):
                raise ValueError('#keyfile,certfile is needed: '
                                 f'{url.fragment}')
            server = \
                gevent.server.StreamServer(
                             bind_addr,
                             proto(**kwargs),
                     keyfile=keyfile,
                    certfile=certfile
                )
        else:
            server = \
                gevent.server.StreamServer(
                    bind_addr,
                    proto(**kwargs)
                )
    server.init_socket()
    real_ip, real_port, *_ = server.socket.getsockname()
    return server, (real_ip, real_port), url.scheme

def get_client(uri):
    ns = get_server(uri, is_via=True)
    return ns.new()

def parse_addr(s):
    host, sep, port = s.rpartition(':')
    port = -1 if not port else int(port)
    if not host:
        host = '0.0.0.0'
    elif len(host) >= 4 and host[0] == '[' and host[-1] == ']':
        host = host[1:-1]
    try:
        return (ipaddress.ip_address(host), port)
    except ValueError:
        return (host, port)

def parse_source_ip(qs, kwargs):
    source_ip = qs['source_ip'][0]
    if source_ip in ['in', 'same']:
        ip = ipaddress.ip_address(kwargs['bind_addr'][0])
        if not ip.is_loopback:
            source_ip = str(ip)
    return (source_ip, 0)

ServerInfo = \
    collections.namedtuple(
        'ServerInfo',
        [
            'server',
            'addr',
            'scheme'
        ]
    )

regex_scheme = re.compile(r'^\w+://')
via_example = 'pass://chacha20:password@127.0.0.1:8080/host/path/'
