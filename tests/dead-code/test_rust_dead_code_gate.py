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

TESTS = "app/tests/values.rs"
ENTRY_POINT = "pub fn entry() -> u32 {\n    {body}\n}\n"
CLEAN_TESTS = "#[test]\nfn enters() {\n    assert!(app::entry() > 0);\n}\n"
COLLECTION_LENGTHS = {
    "HashMap": "HashMap::<u32, u32>::new().len()",
    "HashSet": "HashSet::<u32>::new().len()",
    "BTreeMap": "BTreeMap::<u32, u32>::new().len()",
}
name_suffixes = st.from_regex(r"[a-z]{2,8}", fullmatch=True)


def _verdict(files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        rust_package(root, RUST_MANIFEST)

        for relative, source in files.items():
            stage_file(root, relative, source)

        finished = run_rust_check(root, RUST_CONFIGURATION, "dead-code")

    return finished.returncode, finished.stdout + finished.stderr


def _entry_returning(body: str) -> str:
    return ENTRY_POINT.replace("{body}", body)


@HYPOTHESIS_SETTINGS
@given(name_suffixes, st.booleans())
def test_dead_code_property_fails_only_on_a_rust_function_nobody_calls(
    name_suffix: str, is_called: bool
) -> None:
    name = f"forgotten_{name_suffix}"
    entry_body = f"{name}()" if is_called else "2"
    forgotten = f"\nfn {name}() -> u32 {{\n    1\n}}\n"
    library = _entry_returning(entry_body) + forgotten

    returncode, output = _verdict({RUST_LIBRARY: library, TESTS: CLEAN_TESTS})

    assert returncode == int(not is_called), output
    assert (name in output) == (not is_called)


@HYPOTHESIS_SETTINGS
@given(st.sampled_from(sorted(COLLECTION_LENGTHS)), st.booleans())
def test_dead_code_property_fails_only_on_an_unused_rust_import(
    collection: str, is_used: bool
) -> None:
    entry_body = "1"

    if is_used:
        entry_body = f"{COLLECTION_LENGTHS[collection]} as u32 + 1"

    library = (
        f"use std::collections::{collection};\n\n"
        + _entry_returning(entry_body)
    )

    returncode, output = _verdict({RUST_LIBRARY: library, TESTS: CLEAN_TESTS})

    assert returncode == int(not is_used), output


@HYPOTHESIS_SETTINGS
@given(name_suffixes, st.integers(min_value=1, max_value=5))
def test_dead_code_property_keeps_rust_code_reached_through_a_chain(
    name_suffix: str, chain_length: int
) -> None:
    functions: list[str] = [_entry_returning(f"link_{name_suffix}_0()")]

    for link in range(chain_length):
        is_last = link + 1 == chain_length
        next_call = "1" if is_last else f"link_{name_suffix}_{link + 1}()"
        functions.append(
            f"fn link_{name_suffix}_{link}() -> u32 {{\n    {next_call}\n}}\n"
        )

    library = "\n".join(functions)

    returncode, output = _verdict({RUST_LIBRARY: library, TESTS: CLEAN_TESTS})

    assert returncode == 0, output


@HYPOTHESIS_SETTINGS
@given(name_suffixes, st.booleans())
def test_dead_code_property_fails_on_a_tests_helper_nobody_calls(
    name_suffix: str, is_called: bool
) -> None:
    helper = f"helper_{name_suffix}"
    assertion = f"app::entry() == {helper}()" if is_called else "true"
    tests = (
        f"fn {helper}() -> u32 {{\n    1\n}}\n\n"
        f"#[test]\nfn enters() {{\n    assert!({assertion});\n}}\n"
    )

    returncode, output = _verdict(
        {RUST_LIBRARY: _entry_returning("1"), TESTS: tests}
    )

    assert returncode == int(not is_called), output
    assert (helper in output) == (not is_called)


@HYPOTHESIS_SETTINGS
@given(name_suffixes)
def test_dead_code_property_ignores_a_lint_that_is_not_dead_code(
    name_suffix: str,
) -> None:
    name = f"value_{name_suffix}"
    library = (
        _entry_returning(f"{name}()")
        + f"\nfn {name}() -> u32 {{\n    return 1;\n}}\n"
    )

    returncode, output = _verdict({RUST_LIBRARY: library, TESTS: CLEAN_TESTS})

    assert returncode == 0, output
