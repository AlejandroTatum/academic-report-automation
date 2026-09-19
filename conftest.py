"""Repository-root pytest hook: keep every test off the real content root.

pytest imports the conftest.py closest to its rootdir before it collects a
single test module, so this file runs before ``tools/conftest.py`` and before
any test imports ``report_config`` (which resolves ``CONTENT_ROOT`` once, at
import time, from ``REPORT_CONTENT_ROOT``). Setting the env var here --
unconditionally, even if a developer already exported it -- guarantees no
test run, no matter which module collects first, can read or write the real
private coursework tree at ``~/devwork/.projects/university/...``.

The directory is created fresh per test session and removed at process exit;
nothing under it is meant to outlive the run.
"""
from __future__ import annotations

import atexit
import os
import shutil
import tempfile

_SCRATCH_CONTENT_ROOT = tempfile.mkdtemp(prefix="report-content-root-")
os.environ["REPORT_CONTENT_ROOT"] = _SCRATCH_CONTENT_ROOT
atexit.register(shutil.rmtree, _SCRATCH_CONTENT_ROOT, ignore_errors=True)
