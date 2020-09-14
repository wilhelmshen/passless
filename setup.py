#!/usr/bin/env python3

import re
import setuptools

with open('src/passless/__init__.py') as f:
    version = re.search(r"__version__\s*=\s*'(.*)'", f.read()).group(1)
with open('README.rst') as f:
    readme  = f.read()

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
                 'console_scripts': ['passless=passless.__main__:main']
             }
)
