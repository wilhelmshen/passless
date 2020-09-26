#!/usr/bin/env python3

import os
import os.path
import re
import setuptools
import shutil
import sys
import zipfile

proxychains_zip = 'proxychains-4.2.0.zip'

with open('src/passless/__init__.py') as f:
    version = re.search(r"__version__\s*=\s*'(.*)'", f.read()).group(1)
with open('README.rst') as f:
    readme  = f.read()

class ZipFile(zipfile.ZipFile):

    def extract(self, member, path=None, pwd=None):
        if not isinstance(member, zipfile.ZipInfo):
            member = self.getinfo(member)
        if path is None:
            path = os.getcwd()
        ret_val = self._extract_member(member, path, pwd)
        attr = member.external_attr >> 16
        os.chmod(ret_val, attr)
        return ret_val

class specialized_build_ext(setuptools.command.build_ext.build_ext):

    """
    Specialized builder for libproxychains
    """

    def build_extension(self, ext):
        if 'passless.libproxychains4' == ext.name:
            self.build_extension_libproxychains4(ext)
        else:
            super(specialized_build_ext, self).build_extension(ext)

    def build_extension_libproxychains4(self, ext):
        platform = sys.platform.lower()
        if 'linux' in platform or 'bsd' in platform:
            libproxychains4 = 'libproxychains4.so'
        elif 'darwin' == platform:
            libproxychains4 = 'libproxychains4.dylib'
        else:
            raise NotImplementedError(f'the platform "{sys.platform}" '
                                    'is not currently supported')
        temp_src = \
            os.path.join(
                self.build_temp,
                os.path.splitext(proxychains_zip)[0]
            )
        temp_lib = os.path.join(temp_src, libproxychains4)
        dist_lib = \
            os.path.join(
                self.build_lib,
                'passless',
                libproxychains4
            )
        if not os.path.isdir(temp_src):
            if not os.path.isdir(self.build_temp):
                os.makedirs(self.build_temp)
            src = \
                os.path.abspath(
                    os.path.join(
                        os.path.dirname(__file__),
                        'deps',
                        proxychains_zip
                    )
                )
            with ZipFile(src) as f:
                f.extractall(self.build_temp)
        if not os.path.isfile(temp_lib):
            make_process = \
                subprocess.Popen(
                    './configure && make',
                    cwd=temp_src,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                )
            stdout, stderr = make_process.communicate()
            distutils.log.debug(stdout)
            if stderr:
                raise \
                    distutils.errors.DistutilsSetupError(
                        'An ERROR occured while running the Makefile for '
                        'the libproxychains library. Error status: '
                        f'{stderr}'
                    )
        if not os.path.isfile(dist_lib):
            shutil.copy(temp_lib, dist_lib)

setuptools.setup(
                name='passless',
             version=version,
         description=('A toolkit for setting up a security layer to '
                      'protect private services'),
    long_description=readme,
             license='MIT',
            keywords='gevent asynchronous socks',
              author='Wilhelm Shen',
        author_email='wilhelmshen@pyforce.com',
                 url='http://passless.pyforce.com',
         package_dir={'': 'src'},
            packages=
             [
                 'passless',
                 'passless.proxies',
                 'passless.proxies.base',
                 'passless.proxies.http',
                 'passless.proxies.passless',
                 'passless.proxies.socks'
             ],
    install_requires=
             [
                 'shadowproxy>=0.7.0',
                 'slowdown'
             ],
         ext_modules=
             [
                 setuptools.extension.Extension(
                    'passless.libproxychains4',
                    sources=[]
                 )
             ],
            cmdclass={'build_ext': specialized_build_ext},
         classifiers=
             [
                 'License :: OSI Approved :: MIT License',
                 'Programming Language :: Python :: 3.6',
                 'Programming Language :: Python :: 3.7',
                 'Programming Language :: Python :: 3.8',
                 'Programming Language :: Python :: 3.9',
                 'Programming Language :: Python :: Implementation :: '+
                                                              'CPython',
                 'Operating System :: POSIX',
                 'Topic :: Internet',
                 'Topic :: Software Development :: Libraries :: '+
                                                 'Python Modules',
                 'Intended Audience :: Developers',
                 'Development Status :: 4 - Beta'
             ],
     python_requires='>=3.6',
        entry_points=
             {
                 'console_scripts':
                     [
                            'passless=passless.passless:main',
                         'proxychains=passless.proxychains:main'
                     ]
             }
)
