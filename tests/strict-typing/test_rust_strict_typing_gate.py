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
CLEAN_LIBRARY = "pub fn twice(number: u32) -> u32 {\n    number * 2\n}\n"
CLEAN_TESTS = "#[test]\nfn doubles() {\n    assert_eq!(app::twice(2), 4);\n}\n"
SILENCED_PLACES = (RUST_LIBRARY, TESTS)
name_suffixes = st.from_regex(r"[a-z]{2,8}", fullmatch=True)
silencers = st.sampled_from(
    [
        "#[allow(dead_code)]",
        "#![allow(unused)]",
        "# [ allow ( clippy::all ) ]",
        "#[expect(dead_code)]",
        "#![expect(clippy::pedantic)]",
        "#[cfg_attr(test, allow(dead_code))]",
        "#[cfg_attr(not(test), expect(unused))]",
        "#![ cfg_attr ( feature = \"x\" , allow ( unused ) ) ]",
    ]
)


def _verdict(files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        rust_package(root, RUST_MANIFEST)

        for relative, source in files.items():
            stage_file(root, relative, source)

        finished = run_rust_check(root, RUST_CONFIGURATION, "strict-typing")

    return finished.returncode, finished.stdout + finished.stderr


@HYPOTHESIS_SETTINGS
@given(silencers, st.sampled_from(SILENCED_PLACES))
def test_strict_typing_property_fails_on_every_rust_silencer_spelling(
    silencer: str, silenced_file: str
) -> None:
    files = {RUST_LIBRARY: CLEAN_LIBRARY, TESTS: CLEAN_TESTS}
    files[silenced_file] = f"{silencer}\n{files[silenced_file]}"

    returncode, output = _verdict(files)

    assert returncode == 1, output
    assert f"{silenced_file}:1:" in output


@HYPOTHESIS_SETTINGS
@given(name_suffixes, st.booleans())
def test_strict_typing_property_fails_only_on_a_rust_type_error(
    name_suffix: str, is_mistyped: bool
) -> None:
    returned_value = '"one"' if is_mistyped else "1"
    library = (
        CLEAN_LIBRARY
        + f"\npub fn value_{name_suffix}() -> u32 {{\n"
        + f"    {returned_value}\n}}\n"
    )

    returncode, output = _verdict({RUST_LIBRARY: library, TESTS: CLEAN_TESTS})

    assert returncode == int(is_mistyped), output


@HYPOTHESIS_SETTINGS
@given(name_suffixes, st.booleans())
def test_strict_typing_property_fails_only_on_a_rust_compiler_warning(
    name_suffix: str, is_misnamed: bool
) -> None:
    function_name = f"Value{name_suffix}" if is_misnamed else "value_x"
    library = (
        CLEAN_LIBRARY + f"\npub fn {function_name}() -> u32 {{\n    1\n}}\n"
    )

    returncode, output = _verdict({RUST_LIBRARY: library, TESTS: CLEAN_TESTS})

    assert returncode == int(is_misnamed), output


@HYPOTHESIS_SETTINGS
@given(name_suffixes, st.sampled_from(["allow", "expect"]))
def test_strict_typing_property_never_flags_a_name_that_only_reads_alike(
    name_suffix: str, lint_level: str
) -> None:
    helper_name = f"{lint_level}_{name_suffix}"
    library = (
        CLEAN_LIBRARY
        + f"\npub fn {helper_name}(number: u32) -> u32 {{\n"
        + "    number + 1\n}\n\n"
        + f"pub fn uses_{name_suffix}() -> u32 {{\n"
        + f"    {helper_name}(1)\n}}\n"
    )

    returncode, output = _verdict({RUST_LIBRARY: library, TESTS: CLEAN_TESTS})

    assert returncode == 0, output
