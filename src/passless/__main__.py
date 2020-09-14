# Copyright (c) 2020 Wilhelm Shen. See LICENSE for details.

import argparse
import collections
import copy
import gevent
import gevent.exceptions
import gevent.signal
import os
import os.path
import resource
import slowdown.fs
import slowdown.gvars
import slowdown.sysutil
import sys
import weakref

from . import runtime
from . import utils
from . import   __doc__   as package__doc__
from . import __version__
from .get_server import get_server

default_verbose = 1

def main(**kwargs):
    (   "main("
            "arguments:List[str]=None"
        ") -> None"
    )
    try:
        jobs = spawn(**kwargs)
    except SystemExit as err:
        sys.exit(err.code)
    try:
        gevent.joinall(jobs)
    except gevent.exceptions.BlockingSwitchOutError:
        pass

class Application(object):

    __slots__ = ['args',
                 'fs',
                 'jobs',
                 'opts',
                 'pid',
                 'servers',
                 '__weakref__']

    def exit(self, *args):
        for server in self.servers:
            server.stop()
        if getattr(self, 'jobs', None):
            try:
                gevent.killall(self.jobs)
            except gevent.exceptions.BlockingSwitchOutError:
                pass
            self.jobs = None

def spawn(**kwargs):
    opts, args, parser = parse(**kwargs)
    slowdown.gvars.logger.level = slowdown.gvars.levels[opts.verbose]
    # --root: root dir, probably $HOME/var
    if os.path.isdir(opts.root):
        os.chdir(opts.root)
    else:
        slowdown.gvars.logger.warning(f'No such directory: {opts.root}')
    try:
        resource.setrlimit(resource.RLIMIT_NOFILE, (50000, 50000))
    except Exception:
        slowdown.gvars.logger.warning(
            'Require root permission to allocate resources'
        )
    # Add $HOME/pkgs that contains the user package to sys.path
    pkgs_dir = os.path.join(opts.home, 'pkgs')
    if pkgs_dir not in sys.path:
        sys.path.append(pkgs_dir)
    fs_  = slowdown.fs.FS()
    jobs = Jobs(fs_.spawn())
    app  = Application()
    app.fs   = fs_
    app.jobs = jobs
    app.opts = opts
    app.args = args
    app.pid  = os.getpid()
    app.servers = []
    runtime.application = app
    servers     = []
    ss_filters  = []
    slowdown.gvars.logger.info(f'{__package__}/{__version__}')
    for uri in args.servers:
        try:
            server_info = get_server(uri)
        except Exception as err:
            slowdown.gvars.logger.debug(utils.exc())
            parser.error(str(err))
        servers.append(server_info)
    for server, (host, port), scheme in servers:
        server.start()
        app.servers.append(server)
        ss_filters.append(f'dport = {port}')
        slowdown.gvars.logger.info(
            f'Serving {scheme.upper()} on {host} port {port} ...'
        )
    slowdown.gvars.logger.debug(
        f'sudo lsof -p {app.pid} -P | grep -e TCP -e STREAM'
    )
    slowdown.gvars.logger.debug(f'ss -o "( {" or ".join(ss_filters)} )"')
    exit = exit_func(weakref.ref(app))
    gevent.signal.signal(gevent.signal.SIGQUIT, exit)
    gevent.signal.signal(gevent.signal.SIGTERM, exit)
    gevent.signal.signal(gevent.signal.SIGINT , exit)
    if opts.user is not None:
        try:
            slowdown.sysutil.setuid(opts.user)
        except Exception as err:
            parser.error(f'{err}')
    return jobs

def exit_func(_app):

    def wrapper(*args):
        app = _app()
        if app is not None:
            app.exit()

    return wrapper

class Jobs(list):

    __slots__ = ['_application']

###########################################################################
#                         Command line interface                          #
###########################################################################

def parse(**kwargs):
    defaults  = copy.copy(kwargs)
    arguments = defaults.pop('arguments', None)
    defaults.setdefault('verbose', default_verbose)
    parser    = ParserFactory(**defaults)
    args      = parser.parse_args(arguments)
    opts      = Options()
    opts.user = args.user
    opts.home = args.home
    if args.root is None:
        opts.root = get_default_root(args.home)
    else:
        opts.root = args.root
    if   args.quiet:
        opts.verbose = 0
    elif args.verbose is None:
        opts.verbose = defaults['verbose']
    else:
        assert isinstance(args.verbose, int)
        max_verbose = len(slowdown.gvars.levels) - 1
        if args.verbose >= max_verbose:
            opts.verbose = max_verbose
        else:
            opts.verbose = args.verbose
    return ParseResult(opts, args, parser)

def ParserFactory(**kwargs):
    parser = \
        argparse.ArgumentParser(
                description=package__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
    if kwargs.get('user') is None:
        parser.add_argument(
                    '-u',
                    '--user',
               dest='user',
               type=str,
            metavar='USER',
               help=('server will running as the specified user, '
                     'the default is the current user')
        )
    else:
        parser.add_argument(
                    '-u',
                    '--user',
               dest='user',
               type=str,
            metavar='USER',
               help=('server will running as the specified user, '
                     f'the default is "{kwargs["user"]}"'),
            default=kwargs['user']
        )
    if 'home' not in kwargs:
        default_home = \
            os.path.abspath(
                os.path.join(
                    os.path.dirname(sys.argv[0]),
                    os.path.pardir
                )
            )
    else:
        default_home = kwargs['home']
    parser.add_argument(
                '--home',
           dest='home',
           type=str,
        metavar='DIRECTORY',
           help=f'home dir, the default is {default_home}',
        default=default_home
    )
    if kwargs.get('root') is None:
        default_root = get_default_root(default_home)
        parser.add_argument(
                    '--root',
               dest='root',
               type=str,
            metavar='DIRECTORY',
               help='working dir, the default is $HOME/var',
            default=None
        )
    else:
        parser.add_argument(
                    '--root',
               dest='root',
               type=str,
            metavar='DIRECTORY',
               help=f'working dir, the default is {kwargs["root"]}',
            default=kwargs['root']
        )
    default_verbose = kwargs.get('verbose')
    group = parser.add_mutually_exclusive_group()
    if default_verbose is None or 0 == default_verbose:
        group.add_argument(
                    '-v',
                    '--verbose',
               dest='verbose',
             action='count',
               help='print debug messages to stdout',
        )
        group.add_argument(
                    '-q',
                    '--quiet',
               dest='quiet',
             action='store_true',
               help='do not print debug messages (default)',
            default=False
        )
    else:
        group.add_argument(
                    '-v',
                    '--verbose',
               dest='verbose',
             action='count',
               help=('print debug messages, the default is '
                     f'"-{"v" * default_verbose}"'),
        )
        group.add_argument(
                    '-q',
                    '--quiet',
               dest='quiet',
             action='store_true',
               help='do not print debug messages to stdout',
            default=False
        )
    parser.add_argument(
                    'servers',
              nargs='+',
               type=str
    )
    return parser

class Options(object):

    __slots__ = ['home', 'root', 'user', 'verbose']

ParseResult = \
    collections.namedtuple(
        'ParseReslt',
        [
            'args',
            'opts',
            'parser'
        ]
    )

def get_default_root(home):
    return os.path.join(home, 'var')

if '__main__' == __name__:
    main()
