import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from check_support import HYPOTHESIS_SETTINGS, repository, stage_file
from rust_support import (
    RUST_CONFIGURATION,
    RUST_LIBRARY,
    RUST_MANIFEST,
    run_rust_check,
    rust_package,
    rust_workspace,
)

TESTS = "app/tests/values.rs"
NEEDLESS_RETURN_BODY = "    return 1;\n"
PLAIN_BODY = "    1\n"
name_suffixes = st.from_regex(r"[a-z]{2,8}", fullmatch=True)
member_names = st.sampled_from(["first", "second"])


def _value_function(name: str, body: str) -> str:
    return f"pub fn {name}() -> i32 {{\n{body}}}\n"


def _body_of(is_returned_needlessly: bool) -> str:
    if is_returned_needlessly:
        return NEEDLESS_RETURN_BODY

    return PLAIN_BODY


def _verdict(files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        rust_package(root, RUST_MANIFEST)

        for relative, source in files.items():
            stage_file(root, relative, source)

        finished = run_rust_check(root, RUST_CONFIGURATION, "linters")

    return finished.returncode, finished.stdout + finished.stderr


def _test_file(name: str) -> str:
    return (
        "#[test]\n"
        f"fn {name}_is_one() {{\n"
        f"    assert_eq!(app::{name}(), 1);\n"
        "}\n"
    )


@HYPOTHESIS_SETTINGS
@given(name_suffixes, st.booleans())
def test_linters_property_fails_only_on_a_clippy_warning(
    name_suffix: str, is_returned_needlessly: bool
) -> None:
    name = f"value_{name_suffix}"

    returncode, output = _verdict(
        {
            RUST_LIBRARY: _value_function(
                name, _body_of(is_returned_needlessly)
            ),
            TESTS: _test_file(name),
        }
    )

    assert returncode == int(is_returned_needlessly), output
    assert ("needless_return" in output) == is_returned_needlessly


@HYPOTHESIS_SETTINGS
@given(name_suffixes, st.booleans())
def test_linters_property_fails_only_on_unformatted_rust(
    name_suffix: str, is_formatted: bool
) -> None:
    name = f"value_{name_suffix}"
    formatted = _value_function(name, PLAIN_BODY)
    unformatted = f"pub fn {name}( ) -> i32 {{ 1 }}\n"
    library = formatted if is_formatted else unformatted

    returncode, output = _verdict(
        {RUST_LIBRARY: library, TESTS: _test_file(name)}
    )

    assert returncode == int(not is_formatted), output
    assert ("run cargo fmt" in output) == (not is_formatted)


@HYPOTHESIS_SETTINGS
@given(name_suffixes, st.booleans())
def test_linters_property_lints_the_rust_tests_folder_too(
    name_suffix: str, is_returned_needlessly: bool
) -> None:
    name = f"value_{name_suffix}"
    helper = _value_function(
        f"helper_{name_suffix}", _body_of(is_returned_needlessly)
    )
    tests = (
        helper.replace("pub fn", "fn")
        + "\n#[test]\n"
        + f"fn {name}_matches_the_helper() {{\n"
        + f"    assert_eq!(app::{name}(), helper_{name_suffix}());\n"
        + "}\n"
    )

    returncode, output = _verdict(
        {RUST_LIBRARY: _value_function(name, PLAIN_BODY), TESTS: tests}
    )

    assert returncode == int(is_returned_needlessly), output


@HYPOTHESIS_SETTINGS
@given(name_suffixes)
def test_linters_property_fails_fast_without_a_cargo_manifest(
    name_suffix: str,
) -> None:
    package = f"crate_{name_suffix}"

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        repository(root)
        stage_file(
            root, f"{package}/src/lib.rs", _value_function("one", PLAIN_BODY)
        )

        finished = run_rust_check(
            root, f'source_directories = ["{package}/src"]\n', "linters"
        )

    assert finished.returncode == 1
    assert f"{package} has no Cargo.toml" in finished.stderr


@HYPOTHESIS_SETTINGS
@given(st.one_of(st.none(), member_names), name_suffixes)
def test_linters_property_names_only_the_failing_workspace_member(
    failing_member: str | None, name_suffix: str
) -> None:
    configuration = (
        'source_directories = ["rust/crates/first/src",'
        ' "rust/crates/second/src"]\n'
    )

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        rust_workspace(root, ["first", "second"])

        for member_name in ("first", "second"):
            is_failing = member_name == failing_member
            library = _value_function(
                f"value_{name_suffix}", _body_of(is_failing)
            )
            stage_file(root, f"rust/crates/{member_name}/src/lib.rs", library)

        finished = run_rust_check(root, configuration, "linters")

    output = finished.stdout + finished.stderr
    assert finished.returncode == int(failing_member is not None), output

    for member_name in ("first", "second"):
        is_named = f"clippy rejected rust/crates/{member_name}" in output
        assert is_named == (member_name == failing_member)
