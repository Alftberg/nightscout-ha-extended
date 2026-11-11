"""Version comparison for stable LoopWorkspace releases."""

import re

RELEASES_URL = "https://github.com/LoopKit/LoopWorkspace/releases"
VERSION = re.compile(r"v?([0-9]+)\.([0-9]+)\.([0-9]+)(?:\.[0-9]+)?")


def release_version(value):
    if isinstance(value, str) and (match := VERSION.fullmatch(value.strip())):
        return tuple(map(int, match.groups()))
    return None
