"""Compatibility import; implementation: solar/model.py."""
if __package__:
    from .solar.model import *  # noqa: F401,F403
else:
    from solar.model import *  # noqa: F401,F403
