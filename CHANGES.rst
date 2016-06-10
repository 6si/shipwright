0.3.3 (unreleased)
------------------

- Fix issue when images are built, but not in git.
- Support .dockerignore files on Py3k
- shipwright 'build' sub-command is no-longer optional
- Support extra tags with '-t'
- Continue the build on failure, defer sys.exit until the end of the build.
- Support short names in TARGETS.
- Removed @curry decorator.
- Removed shipwright.version module.
- Removed purge command.
- Fixed various Python 3 bugs.
- Isolate all git functionality, so as to create pluggable Source Control wrappers.
- More efficient required build detection. (`Issue #18 <https://github.com/6si/shipwright/pull/63>`_)
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
