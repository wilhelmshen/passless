import sys

sys.dont_write_bytecode = True

import argparse
import copy
import os
import os.path
import sysconfig

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

    lib_ext_suffix = \
        os.path.splitext(
            sysconfig.get_config_var('EXT_SUFFIX')
        )[1]
    libproxychains4_so = \
        os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                'libproxychains4' + lib_ext_suffix
            )
        )
    libs = [libproxychains4_so]
    platform = sys.platform.lower()
    if 'linux' in platform:
        if 'LD_PRELOAD' in os.environ:
            libs = set(os.environ['LD_PRELOAD'].split() + libs)
        os.environ['LD_PRELOAD'] = ' '.join(libs)
    elif 'darwin' == platform:
        if 'DYLD_INSERT_LIBRARIES' in os.environ:
            libs = set(os.environ['DYLD_INSERT_LIBRARIES'].split() + libs)
        os.environ['DYLD_INSERT_LIBRARIES'] = ' '.join(libs)
        os.environ['DYLD_FORCE_FLAT_NAMESPACE'] = 1
    else:
        raise NotImplementedError(f'the platform "{sys.platform}" '
                                  'is not currently supported')
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
