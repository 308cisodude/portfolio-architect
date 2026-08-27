#!/usr/bin/env python3
"""Validate a built Gateway image's OpenSSL CLI against the reviewed security floor."""

from __future__ import annotations

import re
import sys
from typing import Final

MINIMUM_OPENSSL: Final = (3, 5, 8)
_VERSION_RE: Final = re.compile(r"^OpenSSL (\d+)\.(\d+)\.(\d+)(?:[ .-]|$)")


def validate(label: str, output: str) -> str:
    """Return bounded build evidence or fail if the version is malformed/too old."""
    if not 1 <= len(label) <= 128 or any(ord(char) < 33 or ord(char) > 126 for char in label):
        raise ValueError("OpenSSL build-evidence label is invalid")
    if not 1 <= len(output) <= 512 or any(ord(char) < 32 or ord(char) > 126 for char in output):
        raise ValueError("OpenSSL version output is invalid")
    match = _VERSION_RE.match(output)
    if match is None:
        raise ValueError("OpenSSL version output is not recognized")
    version = tuple(int(part) for part in match.groups())
    if version < MINIMUM_OPENSSL:
        raise ValueError(
            f"OpenSSL {'.'.join(match.groups())} is below security floor "
            f"{'.'.join(map(str, MINIMUM_OPENSSL))}"
        )
    return f"{label}: {output} (security floor >= {'.'.join(map(str, MINIMUM_OPENSSL))})"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_openssl_runtime.py LABEL 'OpenSSL VERSION ...'", file=sys.stderr)
        return 2
    try:
        evidence = validate(sys.argv[1], sys.argv[2])
    except ValueError as err:
        print(f"{sys.argv[1]}: {err}", file=sys.stderr)
        return 1
    print(evidence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
