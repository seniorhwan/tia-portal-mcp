#!/usr/bin/env python3
"""
Single-entry executable to run all 4 tiers of the TIA Portal MCP E2E test suite.
"""

import sys
import os

# Set root
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from tests.e2e.runner import main

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("--mock")
    main()
