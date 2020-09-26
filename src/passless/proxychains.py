import sys

sys.dont_write_bytecode = True

import copy
import os
import os.path
import argparse

from . import   __doc__   as package__doc__
from . import __version__
from .passless import spawn
from .server import URIArgument

default_remote_port   =  80
shell = {'ash', 'bash', 'csh', 'ksh', 'sh', 'tcsh', 'zsh'}

def main(**kwargs):
    (proto, kwargs, url), program, args, parser = parse(**kwargs)
    host, port = kwargs['bind_addr']
    via = (f'{url.scheme}://{kwargs["username"]}:{kwargs["password"]}@'
           f'{host}:{port}/{kwargs["host"]}{kwargs["path"]}')
    if url.query:
        uri = f'socks://127.0.0.1:0/?via={via}&{url.query}'
    else:
        uri = f'socks://127.0.0.1:0/?via={via}'

    import gevent

    arguments   = ['-q', '--root', '.', uri]
    jobs        = spawn(arguments=arguments)
    application = jobs._application()
    server      = application.servers[0]
    addr        = server.socket.getsockname()
    job         = gevent.spawn(run, addr, program, args)
    job.join()
    application.exit()
    if job.value is None:
        sys.exit(getattr(job.exception, 'errno', 256))
    else:
        sys.exit(job.value)

def run(addr, program, args):

    import gevent.subprocess

    platform = sys.platform.lower()
    if 'linux' in platform or 'bsd' in platform:
        filename = 'libproxychains4.so'
    elif 'darwin' == platform:
        filename = 'libproxychains4.dylib'
    else:
        raise NotImplementedError(f'the platform "{sys.platform}" '
                                  'is not currently supported')
    libproxychains4_so = \
        os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                filename
            )
        )
    if 'linux' in platform or 'bsd' in platform:
        os.environ['LD_PRELOAD'] = libproxychains4_so
    if 'darwin' == platform:
        os.environ['DYLD_INSERT_LIBRARIES'    ] = libproxychains4_so
        os.environ['DYLD_FORCE_FLAT_NAMESPACE'] = 1
    os.environ['PROXYCHAINS_SOCKS5_PORT'] = f'{addr[1]}'
    os.environ['PROXYCHAINS_QUIET_MODE' ] =  '1'
    if program.rpartition(os.path.sep)[2] in shell:
        print (f'\nDetect that you have entered \033[32m{program}\33[0m '
                'in proxy mode, use "exit" to leave later.\n')
    try:
        p = gevent.subprocess.Popen([program] + args)
    except Exception as err:
        print (err, file=sys.stderr)
        return getattr(err, 'errno', 256)
    p.communicate()
    return p.returncode

def parse(**kwargs):
    defaults  = copy.copy(kwargs)
    arguments = defaults.pop('arguments', None)
    if arguments is None:
        arguments = sys.argv[1:]
    parser    = ParserFactory(**defaults)
    args      = parser.parse_args(arguments[:2])
    return (args.via, args.program, arguments[2:], parser)

def ParserFactory(**kwargs):
    parser = \
        argparse.ArgumentParser(
                description=package__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
    parser.add_argument(
                'via',
        metavar='via',
           type=ViaArgument,
           help='remote server (bastion host).'
    )
    parser.add_argument(
                'program',
        metavar='program',
           type=str,
           help='program to be executed.'
    )
    parser.add_argument(
                'args',
        metavar='arg',
          nargs='*',
           help='program arguments.'
    )
    return parser

def ViaArgument(uri):
    return URIArgument(uri, is_via=True)
