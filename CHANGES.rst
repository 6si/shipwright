0.9.0 (2017-06-29)
------------------

- Add better fast-alias error message for missing manifest.
  (`Issue #103 <https://github.com/6si/shipwright/pull/103>`_).
- Retry on error during docker push.
  (`Issue #104 <https://github.com/6si/shipwright/pull/104>`_).
- Pull parent images before build to avoid problems with
  docker-py build not sending credentials.
  (`Issue #102 <https://github.com/6si/shipwright/pull/102>`_).
- Push and tag images as soon as they are built.
  (`Issue #101 <https://github.com/6si/shipwright/pull/101>`_).
- Base the cache key on the globs in Docker COPY/ADD commands.
  (`Issue #98 <https://github.com/6si/shipwright/pull/98>`_).


0.8.0 (2017-06-08)
------------------

- Add proper stack traces for direct registry errors.
  (`Issue #93 <https://github.com/6si/shipwright/pull/93>`_).
- Handle differences between docker over TCP and Unix socket.
  (`Issue #96 <https://github.com/6si/shipwright/pull/96>`_).
- Mark every internal package as private to allow exporting
  of select parts of shipwright publicly.
  (`Issue #99 <https://github.com/6si/shipwright/pull/99>`_).
- Create shipwright.targets.targets function to list available
  docker targets in a repo programaticaly.
  (`Issue #100 <https://github.com/6si/shipwright/pull/100>`_).


0.7.0 (2017-01-13)
------------------

- Depend on docker>=2.0.1.
  (`Issue #91 <https://github.com/6si/shipwright/pull/91>`_).


0.6.6 (2017-01-13)
------------------

- Exprimental --registry-login cache flag to skip creation of already built
  images and speed up tagging. Feature not subject to semver.
  (`Issue #89 <https://github.com/6si/shipwright/pull/89>`_).

0.6.5 (2017-01-08)
------------------

- Fix changelog.


0.6.4 (2017-01-08)
------------------

- Add images command for creating docker save.
  (`Issue #88 <https://github.com/6si/shipwright/pull/88>`_).


0.6.3 (2016-08-24)
------------------

- Push images to the registry in parallel.
  (`Issue #82 <https://github.com/6si/shipwright/pull/82>`_).


0.6.2 (2016-08-23)
------------------

- Also push image target ref so that --pull-cache can pull them.
  (`Issue #81 <https://github.com/6si/shipwright/pull/81>`_).


0.6.1 (2016-08-23)
------------------

- Warn on --pull-cache errors
  (`Issue #80 <https://github.com/6si/shipwright/pull/80>`_).


0.6.0 (2016-08-22)
------------------

- Add --pull-cache to pull images from repository before building.
  (`Issue #49 <https://github.com/6si/shipwright/issues/49>`_).


0.5.0 (2016-08-19)
------------------

- Add --dirty to build from working tree, even when uncommitted and untracked changes exist.
  (`Issue #74 <https://github.com/6si/shipwright/pull/74>`_).
  Thanks `James Pickering <https://github.com/jamespic>`_!
- Ignore images without RepoTags when gathering built_tags to fix a crash
  caused by docker images pulled via RepoDigest.
  (`Issue #77 <https://github.com/6si/shipwright/issues/77>`_).
  Thanks `kgpayne <https://github.com/kgpayne>`_!


0.4.2 (2016-06-16)
------------------

- Correct naming, shipwright builds docker images.
  (`Issue #71 <https://github.com/6si/shipwright/pull/71>`_)
- Allow building with a detached HEAD
  (`Issue #72 <https://github.com/6si/shipwright/pull/72>`_)


0.4.1 (2016-06-15)
------------------

- Fix push crash. (`Issue #70 <https://github.com/6si/shipwright/pull/70>`_)


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
