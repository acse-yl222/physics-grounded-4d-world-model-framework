"""Compatibility import; implementation: flood/model.py."""
if __package__:
    from .flood.model import *  # noqa: F401,F403
else:
    from flood.model import *  # noqa: F401,F403
