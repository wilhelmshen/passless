========
Passless
========

Introduction
------------

Passless is a toolkit for setting up a security layer to protect private
services. It based on Yingbo Gu's `Shadowproxy`__ project and comes with
two components, a plugin of `Slowdown`_ server and a client.

For example, in most cases you have to run a ssh service at least. If you
are having a `Slowdown`_ server, you can force users to access this ssh
service only via the working `Slowdown`_ server (by forbidden non-local
connections to the ssh service). All private services can be protected
under the `Slowdown`_ server who is know as `Bastion Host`.

__ https://github.com/guyingbo/shadowproxy


Installation
------------

Passless are published on the `Python Package Index`__ , and can be
installed with the following command.

.. code-block:: console

    $ pip install -U passless

You can also install Passless directly from a clone of the
`Git repository`__ .

.. code-block:: console

    $ git clone https://github.com/wilhelmshen/passless
    $ cd passless
    $ pip install .

or

.. code-block:: console

    $ pip install git+https://github.com/wilhelmshen/passless

__ https://pypi.org/project/passless/
__ https://github.com/wilhelmshen/passless


Server
------


Server creation
^^^^^^^^^^^^^^^

First, you need to create a `Slowdown`_ server.

.. code-block:: console

    $ virtualenv --python=/usr/bin/python3 myserver
    $ myserver/bin/pip3 install passless
    $ myserver/bin/slowdown --init
    Initialize a project in /PATH/TO/myserver? [Y/n]: Y
    Creating myserver/bin ... exists
    Creating myserver/etc ... exists
    Creating myserver/var ... done
    Creating myserver/pkgs ... done
    Creating myserver/var/log ... done
    Creating myserver/bin/slowdown ... exists
    Creating myserver/etc/slowdown.conf ... done
    DONE! Completed all initialization steps.


Configuration
^^^^^^^^^^^^^

Next, edit the profile. The config file of the slowdown server called
``slowdown.conf`` is placed in the ``etc`` folder. Here's an example:

.. code-block:: apacheconf

    # URL Routing based on regular expression.
    <routers>
        <router ALL>

            # A regular expression to match hosts
            # Group name must be uppercased
            #
            pattern ^(?P<EXAMPLE>example\.com)$$

            <host EXAMPLE>

                # A reqular expression to match PATH_INFO
                #
                pattern ^/passless(?P<PASSLESS>/.*)$$

                <path PASSLESS>
                    handler     passless
                    cipher      aes-128-cfb
                    password    PASSWORD

                    # The forwarding server (optional)
                    #
                    #via passless://CIPHER:PASSWD@BRIDGE.SERVER/HOST/PATH/

                    # Ad block list (optional)
                    #
                    #adblk /PATH/TO/AD/BLOCK.conf

                    # If the direct connection fails, use the forwarding
                    # server instead. The default is "yes".
                    #
                    #autoswitch yes

                    # Deny access to the local ip, the default is "yes"
                    # If you want a Bastion Host for local services, this
                    # option must be setted to "no".
                    #
                    #globalonly yes

                    #accesslog  $LOGS/access-%Y%m.log
                    #errorlog   $LOGS/error-%Y%m.log
                </path>
            </host>

            # More hosts ..
            #
            #<host HOSTNAME>...</host>

        </router>
    </routers>

    <servers>
        <http MY_HTTP_SERVER>
            address  0.0.0.0:8080
            router   ALL
        </http>
    </servers>

Start the server:

.. code-block:: console

    $ myserver/bin/slowdown -vv
    2020-09-14 17:45:49 INFO slowdown/{__version__}
    2020-09-14 17:45:49 INFO Serving HTTP on 0.0.0.0 port 8080 ...

In this case, Passless service is available on
``pass://aes-128-cfb:PASSWORD@example.com:80/example.com/passless/`` .

More details are documented at `Slowdown`_ project.

.. _Slowdown: http://slowdown.pyforce.com/


Client
------


passless
^^^^^^^^

The **passless** command can start the Passless client side server that
support the `socks5` and `http` protocol.

.. code-block:: console

    usage: bin/passless [-h] [-u USER] [-v | -vv | -q] SERVERS

Examples:

.. code-block:: console

    $ sudo bin/passless -vv -u nobody "socks://127.0.0.1:1080/?via=passless://aes-128-cfb:PASSWORD@example.com:8080/example.com:8080/passless/&autoswitch=no&globalonly=no" "http://127.0.0.1:8118/?via=passless://aes-128-cfb:PASSWORD@example.com:8080/example.com:8080/passless/&adblk=my_ad_block.conf"

.. code-block:: console

    $ bin/passless "127.0.0.1:1080?via=aes-128-cfb:PASSWORD@example.com:80/example.com/passless/"

With this socks/http server, you can access private services of the
remote server that running the `Slowdown`_ server with the Passless plugin.

.. note::

    The default scheme is `socks://`, the default via scheme is
    `passless://` .


proxychains
^^^^^^^^^^^

This script is based on Adam Hamsik's `proxychains`_ project.
It automatically starts a temporary local socks server configured to the
remote `Bastion Host`, and bridge the network traffic of the specified
program, just as the original `proxychains`_ does.

Example:

.. code-block:: console

    $ bin/proxychains pass://aes-128-cfb:PASSWORD@example.com:8080/example.com:8080/passles/&autoswitch=no ssh user@example.com

.. code-block:: console

    $ bin/proxychains aes-128-cfb:PASSWORD@example.com:8080/example.com:8080/passles/ bash

    Detect that you have entered bash in proxy mode, use "exit" to leave later.

    $ exit
    exit

.. _proxychains: https://github.com/haad/proxychains


Ad block
--------

You can specify an ad block list for servers and clients (see the case
ablove). The file of the ad block list is very simple, as shown below:

.. code-block::

    domain1 REJECT
    domain2 REJECT
        ...
    domain1 PROXY
    domain2 PROXY
        ...

Example:

.. code-block::

    com.baidu.adscdn REJECT
    com.my-server PROXY
