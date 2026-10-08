"""The current release's execution boundary: macOS only, without side effects."""

import sys


class PlatformRefusal(RuntimeError):
    """Execution was refused before any project, registry, scratch or probe access."""


def require_supported_platform():
    """Refuse unverified platforms without consulting files, environment or processes."""
    if sys.platform != "darwin":
        raise PlatformRefusal(
            "this release is macOS-only; Linux and Windows execution is unsupported "
            "until their native implementation and release checks are complete")
