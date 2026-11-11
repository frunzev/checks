import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from check_support import HYPOTHESIS_SETTINGS, stage_file
from rust_support import (
    RUST_CONFIGURATION,
    RUST_LIBRARY,
    RUST_MANIFEST,
    run_rust_check,
    rust_package,
)

TESTS = "app/tests/sign.rs"
SIGN_LIBRARY = (
    "pub fn sign(number: i32) -> &'static str {\n"
    "    if number < 0 {\n"
    '        return "negative";\n'
    "    }\n"
    '    "positive"\n'
    "}\n"
)
POSITIVE_EXPECTATION = '    assert_eq!(app::sign(1), "positive");\n'
NEGATIVE_EXPECTATION = '    assert_eq!(app::sign(-1), "negative");\n'
LOWEST_PARTIAL_PERCENT = 80
HIGHEST_PARTIAL_PERCENT = 90
module_names = st.from_regex(r"lonely_[a-z]{2,8}", fullmatch=True)
wrong_results = st.from_regex(r"wrong[a-z]{0,6}", fullmatch=True)
low_minimum_percents = st.integers(
    min_value=0, max_value=LOWEST_PARTIAL_PERCENT
)
high_minimum_percents = st.integers(
    min_value=HIGHEST_PARTIAL_PERCENT, max_value=100
)
minimum_percents = low_minimum_percents | high_minimum_percents


def _sign_test(expectations: str) -> str:
    return f"#[test]\nfn signs() {{\n{expectations}}}\n"


def _verdict(
    files: dict[str, str], configuration: str
) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        rust_package(root, RUST_MANIFEST)

        for relative, source in files.items():
            stage_file(root, relative, source)

        finished = run_rust_check(root, configuration, "coverage")

    return finished.returncode, finished.stdout + finished.stderr


@HYPOTHESIS_SETTINGS
@given(st.booleans())
def test_coverage_property_fails_only_on_an_untested_rust_line(
    is_negative_tested: bool,
) -> None:
    expectations = POSITIVE_EXPECTATION

    if is_negative_tested:
        expectations += NEGATIVE_EXPECTATION

    returncode, output = _verdict(
        {RUST_LIBRARY: SIGN_LIBRARY, TESTS: _sign_test(expectations)},
        RUST_CONFIGURATION,
    )

    assert returncode == int(not is_negative_tested), output
    assert ("Uncovered Lines" in output) == (not is_negative_tested)


@HYPOTHESIS_SETTINGS
@given(minimum_percents)
def test_coverage_property_obeys_the_configured_rust_minimum(
    minimum_percent: int,
) -> None:
    configuration = (
        RUST_CONFIGURATION
        + f"[checks.coverage]\nfail-under = {minimum_percent}\n"
    )

    returncode, output = _verdict(
        {
            RUST_LIBRARY: SIGN_LIBRARY,
            TESTS: _sign_test(POSITIVE_EXPECTATION),
        },
        configuration,
    )

    is_below_minimum = minimum_percent >= HIGHEST_PARTIAL_PERCENT
    assert returncode == int(is_below_minimum), output


@HYPOTHESIS_SETTINGS
@given(wrong_results)
def test_coverage_property_fails_on_a_failing_rust_test(
    wrong_result: str,
) -> None:
    expectation = f'    assert_eq!(app::sign(1), "{wrong_result}");\n'

    returncode, output = _verdict(
        {RUST_LIBRARY: SIGN_LIBRARY, TESTS: _sign_test(expectation)},
        RUST_CONFIGURATION,
    )

    assert returncode == 1, output
    assert "the tests of app fail" in output


@HYPOTHESIS_SETTINGS
@given(module_names)
def test_coverage_property_fails_on_a_rust_module_no_test_reaches(
    module_name: str,
) -> None:
    library = f"pub mod {module_name};\n\n" + SIGN_LIBRARY
    lonely_module = "pub fn lonely() -> u32 {\n    1\n}\n"
    expectations = POSITIVE_EXPECTATION + NEGATIVE_EXPECTATION

    returncode, output = _verdict(
        {
            RUST_LIBRARY: library,
            f"app/src/{module_name}.rs": lonely_module,
            TESTS: _sign_test(expectations),
        },
        RUST_CONFIGURATION,
    )

    assert returncode == 1, output
    assert f"src/{module_name}.rs" in output


@HYPOTHESIS_SETTINGS
@given(st.sampled_from(["app/src", "app/src/sub"]))
def test_coverage_property_needs_the_rust_tests_folder_listed(
    listed_folder: str,
) -> None:
    configuration = f'source_directories = ["{listed_folder}"]\n'
    files = {
        RUST_LIBRARY: "pub mod sub;\n",
        "app/src/sub/mod.rs": SIGN_LIBRARY,
        TESTS: _sign_test(POSITIVE_EXPECTATION),
    }

    returncode, output = _verdict(files, configuration)

    assert returncode == 1, output
    assert "add it to source_directories" in output


@HYPOTHESIS_SETTINGS
@given(st.integers(min_value=1, max_value=2))
def test_coverage_property_never_counts_a_deleted_rust_test(
    full_runs: int,
) -> None:
    full_tests = _sign_test(POSITIVE_EXPECTATION + NEGATIVE_EXPECTATION)

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        rust_package(root, RUST_MANIFEST)
        stage_file(root, RUST_LIBRARY, SIGN_LIBRARY)
        stage_file(root, TESTS, full_tests)

        for _ in range(full_runs):
            covered = run_rust_check(root, RUST_CONFIGURATION, "coverage")
            assert covered.returncode == 0, covered.stdout + covered.stderr

        stage_file(root, TESTS, _sign_test(POSITIVE_EXPECTATION))
        finished = run_rust_check(root, RUST_CONFIGURATION, "coverage")

    assert finished.returncode == 1, finished.stdout + finished.stderr
