import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from check_support import HYPOTHESIS_SETTINGS, stage_file
from rust_support import (
    RUST_LIBRARY,
    RUST_MANIFEST,
    WORKSPACE_MANIFEST,
    package_manifest,
    run_rust_check,
    rust_package,
    rust_workspace,
)

CONFIGURATION = 'source_directories = ["app/src"]\n'
TESTS = "app/tests/values.rs"
UNRELATED_LIBRARY = "pub fn one() -> u32 {\n    1\n}\n"
LIBRARIES = {
    "serde": "use serde::Serialize;\n\n#[derive(Serialize)]\npub struct A;\n",
    "regex": "pub fn pattern() -> regex::Regex {\n    todo!()\n}\n",
    "anyhow": "pub fn fail() -> anyhow::Result<()> {\n    Ok(())\n}\n",
}
dependencies = st.sampled_from(sorted(LIBRARIES))
sections = st.sampled_from(["dependencies", "dev-dependencies"])


def _declared(section: str, dependency: str) -> str:
    return f'\n[{section}]\n{dependency} = "1"\n'


def _verdict(manifest: str, files: dict[str, str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        rust_package(root, manifest)

        for relative, source in files.items():
            stage_file(root, relative, source)

        finished = run_rust_check(root, CONFIGURATION, "unused-deps")

    return finished.returncode, finished.stdout + finished.stderr


@HYPOTHESIS_SETTINGS
@given(dependencies, st.booleans())
def test_unused_deps_property_fails_only_on_a_declared_unused_crate(
    dependency: str, is_used: bool
) -> None:
    library = LIBRARIES[dependency] if is_used else UNRELATED_LIBRARY

    returncode, output = _verdict(
        RUST_MANIFEST + _declared("dependencies", dependency),
        {RUST_LIBRARY: library},
    )

    assert returncode == int(not is_used), output
    assert (f"\t{dependency}" in output) == (not is_used)


@HYPOTHESIS_SETTINGS
@given(dependencies, sections)
def test_unused_deps_property_honours_the_machete_ignore_list(
    dependency: str, section: str
) -> None:
    manifest = (
        RUST_MANIFEST
        + _declared(section, dependency)
        + "\n[package.metadata.cargo-machete]\n"
        + f'ignored = ["{dependency}"]\n'
    )

    returncode, output = _verdict(manifest, {RUST_LIBRARY: UNRELATED_LIBRARY})

    assert returncode == 0, output


@HYPOTHESIS_SETTINGS
@given(dependencies, st.booleans())
def test_unused_deps_property_counts_a_crate_used_only_in_tests_as_used(
    dependency: str, is_used: bool
) -> None:
    tests = LIBRARIES[dependency] if is_used else UNRELATED_LIBRARY

    returncode, output = _verdict(
        RUST_MANIFEST + _declared("dependencies", dependency),
        {RUST_LIBRARY: UNRELATED_LIBRARY, TESTS: tests},
    )

    assert returncode == int(not is_used), output


@HYPOTHESIS_SETTINGS
@given(dependencies, st.sampled_from(["first", "second"]))
def test_unused_deps_property_names_only_the_workspace_member_at_fault(
    dependency: str, unused_member: str
) -> None:
    configuration = (
        'source_directories = ["rust/crates/first/src",'
        ' "rust/crates/second/src"]\n'
    )
    workspace_manifest = (
        WORKSPACE_MANIFEST
        + f'\n[workspace.dependencies]\n{dependency} = "1"\n'
    )

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        rust_workspace(root, ["first", "second"])
        stage_file(root, "rust/Cargo.toml", workspace_manifest)

        for member_name in ("first", "second"):
            is_unused = member_name == unused_member
            library = UNRELATED_LIBRARY if is_unused else LIBRARIES[dependency]
            manifest = (
                package_manifest(member_name)
                + f"\n[dependencies]\n{dependency}.workspace = true\n"
            )
            stage_file(root, f"rust/crates/{member_name}/Cargo.toml", manifest)
            stage_file(root, f"rust/crates/{member_name}/src/lib.rs", library)

        finished = run_rust_check(root, configuration, "unused-deps")

    output = finished.stdout + finished.stderr
    assert finished.returncode == 1, output
    assert f"rust/crates/{unused_member}/Cargo.toml" in output

    for member_name in ("first", "second"):
        is_blamed = f"checks: rust/crates/{member_name}/Cargo.toml" in output
        assert is_blamed == (member_name == unused_member)
