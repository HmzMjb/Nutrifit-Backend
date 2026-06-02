"""
conftest.py
════════════════════════════════════════════════════════════════════
NutriFit AI — Pytest Configuration
────────────────────────────────────────────────────────────────────
Registers custom markers, configures test output, and prints a
summary of intentional failures after the session ends.
════════════════════════════════════════════════════════════════════
"""

import pytest


# ─── CUSTOM MARKERS ──────────────────────────────────────────────
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "whitebox: White-box (structural) test cases"
    )
    config.addinivalue_line(
        "markers",
        "blackbox: Black-box (behavioural) test cases"
    )
    config.addinivalue_line(
        "markers",
        "known_fail: Intentionally failing — documents a known bug"
    )
    config.addinivalue_line(
        "markers",
        "basis_path: Basis-path coverage test (McCabe V(G))"
    )
    config.addinivalue_line(
        "markers",
        "boundary: Boundary-value analysis test"
    )
    config.addinivalue_line(
        "markers",
        "performance: Backend SLA / latency test"
    )


# ─── SESSION-END SUMMARY ─────────────────────────────────────────
KNOWN_FAILURES = {
    "WB-TC-07": {
        "test":  "TestGenerateExercisePlan::test_unrecognised_goal_FAIL",
        "root":  "Goal 'body recomposition' not in exercise dataset → error dict returned",
        "fix":   "Add goal-synonym normalisation map before DataFrame filter",
        "file":  "whitebox/test_wb_exercise_plan.py",
    },
}


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    terminalreporter.write_sep("=", "NutriFit AI — Known Intentional Failures")
    for tc_id, info in KNOWN_FAILURES.items():
        terminalreporter.write_line(f"\n  ❌  {tc_id}  ({info['file']})")
        terminalreporter.write_line(f"      Test  : {info['test']}")
        terminalreporter.write_line(f"      Root  : {info['root']}")
        terminalreporter.write_line(f"      Fix   : {info['fix']}")
    terminalreporter.write_line(
        "\n  All other failures are UNEXPECTED — investigate immediately.\n"
    )
