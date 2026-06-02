"""
conftest.py — NutriFit AI pytest configuration
Registers markers and prints known-failure summary at session end.
"""
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "whitebox: White-box structural tests")
    config.addinivalue_line("markers", "blackbox: Black-box behavioural tests")
    config.addinivalue_line("markers", "known_fail: Intentional — documents a known bug")
    config.addinivalue_line("markers", "basis_path: Basis-path coverage (McCabe V(G))")
    config.addinivalue_line("markers", "boundary: Boundary-value analysis")
    config.addinivalue_line("markers", "performance: Backend SLA / latency")

KNOWN_FAILURES = {
    "WB-P4":    {
        "test": "TestBasisPaths::test_path4_all_conditions_KNOWN_FAIL",
        "root": "Stacked allergen+health filters eliminate entire 20-food dataset",
        "fix":  "Add constraint-relaxation fallback when pool < 3 items",
        "file": "whitebox/test_wb_meal_filter.py",
    },
    "WB-TC-07": {
        "test": "TestGenerateExercisePlan::test_unknown_goal_returns_error_KNOWN_FAIL",
        "root": "Goal 'body recomposition' not in excercise.csv → error dict returned",
        "fix":  "Add goal-synonym normalisation map before DataFrame filter",
        "file": "whitebox/test_wb_exercise_profile.py",
    },
}

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    terminalreporter.write_sep("=", "NutriFit AI — Known Intentional Failures")
    for tc_id, info in KNOWN_FAILURES.items():
        terminalreporter.write_line(f"\n  ❌  {tc_id}  ({info['file']})")
        terminalreporter.write_line(f"      Test : {info['test']}")
        terminalreporter.write_line(f"      Root : {info['root']}")
        terminalreporter.write_line(f"      Fix  : {info['fix']}")
    terminalreporter.write_line(
        "\n  All other failures are UNEXPECTED — investigate immediately.\n"
    )
