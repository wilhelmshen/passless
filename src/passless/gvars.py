# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

import uuid

PACKET_SIZE  =  8192
autoswitch_timeout = 5
default_autoswitch = False
default_globalonly = False
accept_language = 'zh-CN,zh;q=0.8,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2'
accept = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
content_type = 'video/mp4'
token_name   = 'STOKEN'
yes = {'y', 'yes', 'on', 'true', 'ok'}
no  = {'n', 'no', 'off', 'false'}

def gen_filename():
    return f'{uuid.uuid4().hex[0:16]}.mp4'