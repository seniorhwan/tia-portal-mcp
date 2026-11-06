"""
Comprehensive CLI Test Runner for TIA Portal MCP E2E Test Suite.
Supports tier filtering, feature filtering, live/mock execution,
and detailed test execution reporting.
"""

import sys
import os
import argparse
import unittest
import time
from typing import List, Dict, Any, Optional

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from tests.e2e.harness.config import ServerConfig
from tests.e2e.harness.base_test import McpTestCase


TIER_MODULE_MAP = {
    1: [
        "tests.e2e.tier1_features.test_handshake",
        "tests.e2e.tier1_features.test_capabilities",
        "tests.e2e.tier1_features.test_lifecycle",
        "tests.e2e.tier1_features.test_plc",
        "tests.e2e.tier1_features.test_network",
        "tests.e2e.tier1_features.test_hmi",
        "tests.e2e.tier1_features.test_vci",
    ],
    2: [
        "tests.e2e.tier2_boundaries.test_malformed_json",
        "tests.e2e.tier2_boundaries.test_rpc_protocol_errors",
        "tests.e2e.tier2_boundaries.test_schema_boundaries",
        "tests.e2e.tier2_boundaries.test_buffer_and_batch_limits",
    ],
    3: [
        "tests.e2e.tier3_combinations.test_session_lifecycle_flow",
        "tests.e2e.tier3_combinations.test_access_mode_boundary_flow",
        "tests.e2e.tier3_combinations.test_guarded_write_audit_flow",
        "tests.e2e.tier3_combinations.test_error_cascading_flow",
    ],
    4: [
        "tests.e2e.tier4_real_world.test_antigravity_discovery",
        "tests.e2e.tier4_real_world.test_absent_tia_degradation",
        "tests.e2e.tier4_real_world.test_fake_worker_roundtrips",
        "tests.e2e.tier4_real_world.test_launcher_script_stdio",
    ],
}

FEATURE_MAP = {
    "handshake": "tests.e2e.tier1_features.test_handshake",
    "capabilities": "tests.e2e.tier1_features.test_capabilities",
    "lifecycle": "tests.e2e.tier1_features.test_lifecycle",
    "plc": "tests.e2e.tier1_features.test_plc",
    "network": "tests.e2e.tier1_features.test_network",
    "hmi": "tests.e2e.tier1_features.test_hmi",
    "vci": "tests.e2e.tier1_features.test_vci",
}


def create_suite(
    tiers: Optional[List[int]] = None,
    feature: Optional[str] = None,
    mock_mode: bool = False,
    server_cmd: Optional[List[str]] = None
) -> unittest.TestSuite:
    """Builds the test suite based on selected tiers or feature filters."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    target_modules = []
    if feature:
        feat_mod = FEATURE_MAP.get(feature.lower())
        if not feat_mod:
            raise ValueError(f"Unknown feature '{feature}'. Available: {list(FEATURE_MAP.keys())}")
        target_modules.append(feat_mod)
    else:
        selected_tiers = tiers or [1, 2, 3, 4]
        for t in selected_tiers:
            target_modules.extend(TIER_MODULE_MAP.get(t, []))

    # Apply mock or server_cmd configuration to base class if requested
    if mock_mode:
        McpTestCase.use_mock_server = True
    if server_cmd:
        ServerConfig.command = server_cmd

    for mod_name in target_modules:
        try:
            mod = __import__(mod_name, fromlist=["*"])
            suite.addTests(loader.loadTestsFromModule(mod))
        except Exception as e:
            print(f"[ERROR] Failed to load test module {mod_name}: {e}", file=sys.stderr)
            raise

    return suite


def run_tests(
    tiers: Optional[List[int]] = None,
    feature: Optional[str] = None,
    mock_mode: bool = False,
    server_cmd: Optional[List[str]] = None,
    verbosity: int = 2
) -> int:
    """Executes the test suite and prints structured summary."""
    print("=" * 70)
    print(" TIA Portal MCP Server E2E Test Runner")
    print("=" * 70)

    if mock_mode:
        print("Mode: Mock Server Oracle (Embedded net10/stdio simulator)")
    elif server_cmd:
        print(f"Mode: Custom Server Command -> {' '.join(server_cmd)}")
    else:
        print("Mode: Auto-detected MCP Server")

    tier_desc = f"Tier(s): {tiers}" if tiers else (f"Feature: {feature}" if feature else "All Tiers (1-4)")
    print(f"Target: {tier_desc}")
    print("-" * 70)

    start_time = time.time()
    suite = create_suite(tiers=tiers, feature=feature, mock_mode=mock_mode, server_cmd=server_cmd)
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("-" * 70)
    print("TEST EXECUTION SUMMARY:")
    print(f"  Total Tests Run: {result.testsRun}")
    print(f"  Passed:          {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Failures:        {len(result.failures)}")
    print(f"  Errors:          {len(result.errors)}")
    print(f"  Skipped:         {len(result.skipped)}")
    print(f"  Duration:        {elapsed:.2f} seconds")
    print("=" * 70)

    return 0 if result.wasSuccessful() else 1


def main():
    parser = argparse.ArgumentParser(description="Run TIA Portal MCP E2E Test Suite")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4], help="Run tests for a single tier")
    parser.add_argument("--feature", type=str, choices=list(FEATURE_MAP.keys()), help="Run tests for a single feature area")
    parser.add_argument("--mock", action="store_true", help="Force execution against embedded mock oracle")
    parser.add_argument("--server-cmd", type=str, help="Custom server command line")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose test execution output")

    args = parser.parse_args()

    server_cmd = None
    if args.server_cmd:
        import shlex
        server_cmd = shlex.split(args.server_cmd)

    tiers = [args.tier] if args.tier else None
    verbosity = 2 if args.verbose else 1

    exit_code = run_tests(
        tiers=tiers,
        feature=args.feature,
        mock_mode=args.mock,
        server_cmd=server_cmd,
        verbosity=verbosity
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
