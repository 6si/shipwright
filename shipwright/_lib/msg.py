from __future__ import absolute_import

from collections import namedtuple


"""
classes for communicating between generators
"""


class Message(object):
    """
    Base class for all other messages
    """


class BuildComplete(Message, namedtuple('BuildComplete', ['target'])):
    """
    A message to signify that the build has finished for a target.

    The build may not have completed succesfully
    """
