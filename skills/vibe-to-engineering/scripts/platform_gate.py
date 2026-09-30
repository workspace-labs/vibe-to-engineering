#!/usr/bin/env python3
"""The one platform this release supports (A4): macOS.

Staged platform releases (owner-frozen decision): macOS first, then Linux, then Windows. No
platform is release-validated until the revised implementation passes its release exam on it,
so every entry point — evidence.py, checkpoint.py, render_pdf.py — refuses to run anywhere
else: before any write, check, launch or platform-risky import, with a plain-language message
that names the platform it saw, never a traceback. There is no bypass: no flag, environment
variable or config lets another platform run. Linux and Windows live in the roadmap only.

Standard library only, and importable on every platform: the entry points import this module
before anything that could fail or act on the refused one.
"""

import sys

SUPPORTED = "darwin"


def platform_refusal(program):
    """The refusal message for `program` on an unsupported platform, or None on macOS."""
    if sys.platform == SUPPORTED:
        return None
    return ("%s: error: this release supports macOS only; Linux and Windows are on the roadmap and not yet "
            "validated. Nothing was run or written. (platform seen: %s)\n" % (program, sys.platform))
