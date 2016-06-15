---
layout: default
title: Shipwright | The right way to build, tag and ship shared Docker images.
---

<strong>Shipwright | The right way to build, tag and 
ship Docker images.</strong>


Shipwright builds shared Docker images within a git repository
in **the right order** and publishes them tagged with git's revision/branch
information so  you'll never loose track of an images origin.

It's the perfect tool for building and publishing your images to places
like Docker Hub or your own private registry. Have a look at  [our motivation](motivation.md) to see why we built it and the pain points it solves for you.


Installation
============

Shipwright is a simple python script you can install with pip

	$ pip install shipwright


Quickstart
==========


Building
--------

Once installed, simply change to a project of yours that contains multiple Dockerfiles and is in git. Then run:

	$ shipwright <docker hub username>
	
This will recurse through all the directories and looking for ones that contain a Dockerfile. Shipwright will build these dockefiles in order and by default tag them with `<docker hub username>/<dirname>`


We have [a sample shipwright project](https://github.com/6si/shipwrigt-sample) you can use if you want to try this out right away.

```bash
$ git clone https://github.com/6si/shipwrigt-sample.git
$ cd shipwright-sample
$ shipwright solomon
```

**NOTE: you can use any username you'd like while building locally. Nothing is published unless you include the `--publish` flag. However  it's probably a good idea to substitue `solomon` in the above example with you (or your organizations) official docker hub username.**

**PRO TIP: if you build a lot, set the `SW_NAMESPACE` environment variable to your username**

Running `shipwright` a second time nothing will return immediatly without doing anything as Shipwright is smart enough to know nothing has changed.

Shipwright really shines when you switch git branches.

```bash
$ git checkout new_feature
$ shipwright solomon
```

Notice that shipwright only rebuilt  the shared library and service1 ignoring the other projects because they have a common git ancestory. Running `docker images` however shows that all the images in the git repository have been tagged with the latest git revision and branch. 

In fact as Shipwright builds  images it rewrites the Dockerfiles so that they require the base images with tags from the current git revision. This ensures that the entire build is deterministic and reproducable.

Publishing
----------
TBD

To publish the built images after building and tagging, simply include the `--publish` flag when running shipwright

```bash
$ shipwright --publish <username> 
```




