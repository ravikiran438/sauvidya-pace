# Copyright 2026 Ravi Kiran Kadaboina
# Licensed under the Apache License, Version 2.0.

"""PACE specification reference types and validators."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pace")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0+unknown"
