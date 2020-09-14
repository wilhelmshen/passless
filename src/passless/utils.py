# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

import gevent.socket
import hashlib
import iofree
import ipaddress
import time
import traceback

from . import gvars

token_expiration_time = 30

def run_parser(parser, sock):
    parser.send(b'')
    while True:
        for to_send, close, exc, result in parser:
            if to_send:
                sock.sendall(to_send)
            if close:
                sock.close()
            if exc:
                raise exc
            if result is not iofree._no_result:
                return result
        data = sock.recv(gvars.PACKET_SIZE)
        if not data:
            raise iofree.ParseError('need data')
        parser.send(data)

def is_global(host):
    if host == 'localhost':
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True
    return address.is_global

def pack_addr(addr) -> bytes:
    host, port = addr
    try:
        packed = b'\x01' + gevent.socket.inet_aton(host)
    except OSError:
        try:
            packed = b'\x04' \
                   + gevent.socket.inet_pton(gevent.socket.AF_INET6, host)
        except OSError:
            packed = host.encode('ascii')
            packed = b'\x03' + len(packed).to_bytes(1, 'big') + packed
    return packed + port.to_bytes(2, 'big')

def check_token(token, password):
    time_stamp = token[16:]
    if len(time_stamp) > 10:
        return False
    if time.time() - int(time_stamp, 16) > token_expiration_time:
        return False
    digest1 = token[0:16]
    digest2 = \
        hashlib.md5(
            hashlib.md5( password .encode()).digest() +
            hashlib.md5(time_stamp.encode()).digest()
        ).hexdigest()[0:16]
    return digest1 == digest2

def make_token(password):
    time_stamp = '%x' % int(time.time())
    digest1 = \
        hashlib.md5(
            hashlib.md5( password .encode()).digest() +
            hashlib.md5(time_stamp.encode()).digest()
        ).hexdigest()[0:16]
    return digest1 + time_stamp

def exc():
    file = tb_file()
    traceback.print_exc(file=file)
    return ''.join(file)

class tb_file(list):

    write = list.append
