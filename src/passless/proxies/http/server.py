# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

import base64
import shadowproxy.protocols.http
import urllib.parse

from ... import utils
from ..base.server import Context, ProxyBase

class HTTPProxy(ProxyBase):

    proto = 'http'

    def _run(self, socket, client_addr):
        parser = shadowproxy.protocols.http.HTTPRequest.get_parser()
        request = utils.run_parser(parser, socket)
        if self.auth:
            pauth    =  request.headers.get(b'Proxy-Authorization', None)
            httpauth = b'Basic ' + base64.b64encode(b':'.join(self.auth))
            if httpauth != pauth:
                socket.sendall(
                    request.ver +
                    b' 407 Proxy Authentication Required\r\n'
                    b'Connection: close\r\n'
                    b'Proxy-Authenticate: '
                    b'Basic realm="Passless Auth"\r\n\r\n'
                )
                raise HTTPException(401, 'Unauthorized HTTP Request')
        if b'CONNECT' == request.method:
            proto         = 'http-connect'
            host, _, port = request.path.partition(b':')
            target_addr   = (host.decode(), int(port))
        else:
            proto = 'http-pass'
            url   = urllib.parse.urlparse(request.path)
            if not url.hostname:
                socket.sendall(
                    b'HTTP/1.1 200 OK\r\n'
                    b'Connection: close\r\n'
                    b'Content-Type: text/plain\r\n'
                    b'Content-Length: 2\r\n\r\n'
                    b'ok'
                )
                return Context(None, None, proto, None)
            target_addr = (url.hostname.decode(), url.port or 80)
            newpath = url._replace(netloc=b'', scheme=b'').geturl()
        via_socket, mode = self.create_connection(target_addr)
        if via_socket is None:
            return Context(None, target_addr, proto, mode)
        if request.method == b'CONNECT':
            socket.sendall(
                b'HTTP/1.1 200 Connection: Established\r\n\r\n'
            )
            remote_req_headers = b''
        else:
            headers_list = \
                [
                    b'%s: %s' % (k, v)
                    for k, v in request.headers.items()
                        if not k.startswith(b'Proxy-')
                ]

            # TODO: HTTPForwardClient
            #if isinstance(via_socket, HTTPForwardClient):
            #    headers_list.extend(via_client.extra_headers)
            #    newpath = url.geturl()

            lines = b'\r\n'.join(headers_list)
            remote_req_headers = \
                b'%s %s %s\r\n%s\r\n\r\n' % \
                (
                    request.method,
                    newpath,
                    request.ver,
                    lines
                )
        redundant = parser.readall()
        to_send = remote_req_headers + redundant
        if to_send:
            via_socket.sendall(to_send)
        return Context(via_socket, target_addr, proto, mode)

class HTTPException(Exception):

    def __init__(self, *args):
        self.errno, self.strerror = args
        self.args = args
