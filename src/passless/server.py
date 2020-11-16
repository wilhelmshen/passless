# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

import argparse
import base64
import collections
import copy
import gevent.server
import gevent.socket
import ipaddress
import re
import shadowproxy.ciphers
import slowdown.gvars
import urllib.parse

from . import gvars
from . import proxies
from .ad_block import get_adblk, ADBLKArgument

default_local_scheme  = 'socks'
default_remote_scheme =  'pass'
default_ports = \
    {
           'http': 8118,
          'https': 443,
        'forward': 80,
           'pass': 80,
       'passless': 80,
            'red': 12345,
          'socks': 1080
    }

def URIArgument(uri, is_via=False):
    if re.search(r'^\w+://', uri) is None:
        if is_via:
            url = urllib.parse.urlparse(f'{default_remote_scheme}://{uri}')
        else:
            url = urllib.parse.urlparse(f'{default_local_scheme}://{uri}')
    else:
        url = urllib.parse.urlparse(uri)
    kwargs = {}
    if is_via:
        try:
            proto = proxies.via_protos[url.scheme]
        except KeyError:
            raise \
                argparse.ArgumentTypeError(
                    f'client scheme "{url.scheme}" is not supported'
                )
    else:
        try:
            proto = proxies.server_protos[url.scheme]
        except KeyError:
            raise \
                argparse.ArgumentTypeError(
                    f'server scheme "{url.scheme}" is not supported'
                )
    userinfo, sep, loc = url.netloc.rpartition('@')
    if userinfo:
        if ':' not in userinfo:
            userinfo = base64.b64decode(userinfo).decode('ascii')
        try:
            username, sep, password = userinfo.partition(':')
        except IndexError:
            raise argparse.ArgumentTypeError(f'invalid user: {userinfo}')
        kwargs['username'] = username
        kwargs['password'] = password
        if url.scheme in ['pass', 'passless', 'ss', 'ssudp']:
            kwargs['cipher'] = shadowproxy \
                             . ciphers     \
                             . ciphers[username](password)
            if not kwargs['cipher'].is_stream_cipher:
                if is_via:
                    proto = proxies.   via_protos['aead']
                else:
                    proto = proxies.server_protos['aead']
        elif url.scheme in ['http', 'https', 'socks', 'forward']:
            kwargs['auth'] = (username.encode(), password.encode())
    elif url.scheme in ['pass', 'passless', 'ss', 'ssudp']:
        raise \
            argparse.ArgumentTypeError(
                f'you need to assign cryto algorithm and password {uri}'
            )
    try:
        host, port = parse_addr(loc)
    except Exception as err:
        raise argparse.ArgumentTypeError(f'{err}')
    if -1 == port:
        try:
            port = default_ports[url.scheme]
        except KeyError:
            if is_via:
                raise \
                    argparse.ArgumentTypeError(
                        'you need to assign remote port'
                    )
            else:
                raise \
                    argparse.ArgumentTypeError(
                        'you need to assign local port'
                    )
    bind_addr = (str(host), port)
    kwargs['bind_addr'] = bind_addr
    if url.scheme in ['pass', 'passless']:
        host, sep, path = url.path.lstrip('/').partition('/')
        if '' == path:
            slowdown.gvars.logger.warning(
                '"/" is used because the remote path is unset, example '
                ':1080?via=pass://cipher:passwd@ip:port/host/path'
            )
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
            raise \
                argparse.ArgumentTypeError(
                    'destitation must be assign in tunnel udp mode, '
                    'example tunneludp://:53/?target=8.8.8.8:53'
                )
        host, port = parse_addr(qs['target'][0])
        kwargs['target_addr'] = (str(host), port)
    if is_via:
        return ParseResult(proto, kwargs, url)
    elif 'via' in qs:
        kwargs['via'] = URIArgument(qs['via'][0], True)
    if 'adblk' in qs:
        kwargs['adblk'] = ADBLKArgument(qs['adblk'][0])
    if 'autoswitch' in qs:
        autoswitch = qs['autoswitch'][0].lower()
        if   autoswitch in gvars.yes:
            kwargs['autoswitch'] = True
        elif autoswitch in gvars.no:
            kwargs['autoswitch'] = False
        else:
            kwargs['autoswitch'] = gvars.default_autoswitch
            if autoswitch != '':
                slowdown.gvars.logger.warning(
                    'ignore unknown autoswitch value '
                    f'{qs["autoswitch"][0]}'
                )
    else:
        kwargs['autoswitch'] = gvars.default_autoswitch
    if 'globalonly' in qs:
        globalonly = qs['globalonly'][0].lower()
        if   globalonly in gvars.yes:
            kwargs['globalonly'] = True
        elif globalonly in gvars.no:
            kwargs['globalonly'] = False
        else:
            kwargs['globalonly'] = gvars.default_globalonly
            if globalonly != '':
                slowdown.gvars.logger.warning(
                    'ignore unknown globalonly value '
                    f'{qs["globalonly"][0]}'
                )
    else:
        kwargs['globalonly'] = gvars.default_globalonly
    if ':' in bind_addr[0]:
        family = gevent.socket.AF_INET6
    else:
        family = gevent.socket.AF_INET
    if url.scheme.endswith('udp'):
        raise argparse.ArgumentTypeError('udp is currently not supported')
    elif 'https' == url.scheme:
        if not url.fragment:
            raise \
                argparse.ArgumentTypeError(
                    '#keyfile,certfile is needed'
                )
        try:
            keyfile, sep, certfile = url.fragment.partition(',')
        except (IndexError, ValueError):
            raise \
                argparse.ArgumentTypeError(
                    f'#keyfile,certfile is needed: {url.fragment}'
                )
        kwargs[ 'keyfile'] =  keyfile
        kwargs['certfile'] = certfile
    return ParseResult(proto, kwargs, url)

def get_server(uri):
    if isinstance(uri, str):
        proto, kwargs, url = URIArgument(uri, is_via=False)
    else:
        proto, kwargs, url = uri
    kwargs = copy.copy(kwargs)
    if  'adblk'  in kwargs:
        kwargs['adblk'] = get_adblk(kwargs.pop('adblk'))
    if   'via'   in kwargs:
        kwargs[ 'via' ] = get_client(kwargs.pop('via'))
    if 'keyfile' in kwargs:
        server = \
            gevent.server.StreamServer(
                         kwargs['bind_addr'],
                         proto(**kwargs),
                 keyfile=kwargs['keyfile'],
                certfile=kwargs['certfile']
            )
    else:
        server = \
            gevent.server.StreamServer(
                kwargs['bind_addr'],
                proto(**kwargs)
            )
    server.init_socket()
    real_ip, real_port, *dummy = server.socket.getsockname()
    return ServerInfo(server, (real_ip, real_port), url.scheme)

def get_client(uri):
    if isinstance(uri, str):
        proto, kwargs, url = URIArgument(uri, is_via=True)
    else:
        proto, kwargs, url = uri
    return proto(**kwargs)

def parse_addr(s):
    host, sep, _port = s.partition(':')
    if not _port:
        port = -1
    else:
        port = int(_port)
    if not host:
        host = '0.0.0.0'
    elif len(host) >= 4 and host[0] == '[' and host[-1] == ']':
        host = host[1:-1]
    try:
        return (ipaddress.ip_address(host), port)
    except ValueError:
        return (host, port)

ParseResult = \
    collections.namedtuple(
        'ParseResult',
        [
            'proto',
            'kwargs',
            'url'
        ]
    )
ServerInfo  = \
    collections.namedtuple(
        'ServerInfo',
        [
            'server',
            'addr',
            'scheme'
        ]
    )
