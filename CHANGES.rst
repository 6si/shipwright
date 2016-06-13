0.4.0 (2016-06-13)
------------------

- Isolate all git functionality, so as to create pluggable Source Control wrappers.
- More efficient required build detection. (`Issue #63 <https://github.com/6si/shipwright/pull/63>`_)
- Isolate all zipper usage, vendor zipper library.

0.2.2 (2015-01-07)
------------------

-  Fix bug missing ``tls`` when communicating with docker over a unix
   socket.

0.2.1 (2015-01-01)
------------------

-  Force tag to support docker 1.4.1
-  Requries docker-py >= 0.6
-  Added ``assert_hostname`` as an option to ``.shipwright.json``
-  Added command line option ``--x-assert-hostname`` to disable hostname
   checking when TLS is used. Useful for boot2docker

0.2.0 (2014-12-31)
------------------

-  Added ``shipwright push`` and ``shipwright purge``
-  Added support for specifiers ``-u``, ``-d``, ``-e`` and ``-x``

0.1.0 (2014-09-10)
------------------

-  Build and tag containers
-  Moved config to ``.shipwright.json``
