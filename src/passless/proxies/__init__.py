# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

from  .http.server import HTTPProxy
from  .passless.client import PasslessClient
from  .socks.server import SocksProxy

server_protos = \
    {
            'http': HTTPProxy,
           'socks': SocksProxy
    }
via_protos    = \
    {
            'pass': PasslessClient,
        'passless': PasslessClient
    }
