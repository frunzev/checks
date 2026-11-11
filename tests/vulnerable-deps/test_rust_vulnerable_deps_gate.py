import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from check_support import (
    COPIED_TOOLKIT,
    HYPOTHESIS_SETTINGS,
    here_document,
    repository,
    stage_file,
)
from rust_support import (
    RUST_MANIFEST,
    RUST_TOOL_ROOT,
    WORKSPACE_MANIFEST,
    package_manifest,
    run_rust_check,
    rust_package,
)

CONFIGURATION = 'source_directories = ["app/src"]\n'
VULNERABLE_CRATES = {
    "RUSTSEC-2022-0013": ("regex", "1.5.4"),
    "RUSTSEC-2021-0003": ("smallvec", "1.6.0"),
}
CRATES_IO = "registry+https://github.com/rust-lang/crates.io-index"
LOCKFILE_HEADER = (
    'version = 4\n\n[[package]]\nname = "app"\nversion = "0.1.0"\n'
)
UNREACHABLE_ERROR = (
    "error: couldn't fetch advisory database: git operation failed: An IO"
    " error occurred when talking to the server\n"
    "  -> error sending request for url"
    " (https://github.com/RustSec/advisory-db.git/info/refs)\n"
)
BROKEN_LOCKFILE_ERROR = (
    "error: not found: Couldn't load Cargo.lock\n"
    "  -> parse error: TOML parse error at line 1, column 12\n"
)
VULNERABLE_REPORT = "Crate: regex\nID: RUSTSEC-2022-0013\n"
REAL_AUDIT_SETTINGS = settings(max_examples=4, deadline=None)
advisory_ids = st.lists(
    st.from_regex(r"RUSTSEC-20[0-9]{2}-[0-9]{4}", fullmatch=True),
    max_size=4,
)
member_counts = st.integers(min_value=1, max_value=3)


def _lockfile(crates: list[tuple[str, str]]) -> str:
    sections = [LOCKFILE_HEADER]

    for name, version in crates:
        sections.append(
            f'[[package]]\nname = "{name}"\nversion = "{version}"\n'
            f'source = "{CRATES_IO}"\n'
        )

    return "\n".join(sections)


def _stub_audit(root: Path, body: str) -> Path:
    calls = root / "audit-calls"
    stub = root / COPIED_TOOLKIT / RUST_TOOL_ROOT / "bin" / "cargo-audit"
    stub.parent.mkdir(parents=True)
    recorder = f'printf "%s\\n" "$*" >> "{calls}"\n'
    _ = stub.write_text(f"#!/bin/sh\n{recorder}{body}", encoding="utf-8")
    stub.chmod(0o755)

    return calls


def _stubbed_package(root: Path, body: str) -> Path:
    repository(root)
    calls = _stub_audit(root, body)
    stage_file(root, "app/Cargo.toml", RUST_MANIFEST)
    stage_file(root, "app/src/lib.rs", "pub fn one() -> u32 {\n    1\n}\n")
    stage_file(root, "app/Cargo.lock", _lockfile([]))

    return calls


def _whitelisted(whitelist: list[str]) -> str:
    quoted_ids: list[str] = []

    for advisory_id in whitelist:
        quoted_ids.append(f'"{advisory_id}"')

    listed_ids = ", ".join(quoted_ids)
    whitelist_section = f"whitelist = [{listed_ids}]\n"

    return CONFIGURATION + "[checks.vulnerable-deps]\n" + whitelist_section


@REAL_AUDIT_SETTINGS
@given(st.sets(st.sampled_from(sorted(VULNERABLE_CRATES))))
def test_vulnerable_deps_property_reports_exactly_the_unaccepted_advisories(
    accepted_ids: set[str],
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        rust_package(root, RUST_MANIFEST)
        stage_file(root, "app/src/lib.rs", "pub fn one() -> u32 {\n    1\n}\n")
        crates = list(VULNERABLE_CRATES.values())
        stage_file(root, "app/Cargo.lock", _lockfile(crates))

        finished = run_rust_check(
            root, _whitelisted(sorted(accepted_ids)), "vulnerable-deps"
        )

    unaccepted_ids = set(VULNERABLE_CRATES) - accepted_ids
    assert finished.returncode == int(bool(unaccepted_ids)), finished.stderr

    for advisory_id in VULNERABLE_CRATES:
        is_reported = advisory_id in finished.stderr
        assert is_reported == (advisory_id in unaccepted_ids)


@HYPOTHESIS_SETTINGS
@given(st.sampled_from([UNREACHABLE_ERROR, BROKEN_LOCKFILE_ERROR]))
def test_vulnerable_deps_property_skips_only_an_unreachable_database(
    audit_error: str,
) -> None:
    body = here_document("ERROR", audit_error) + "exit 1\n"

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _ = _stubbed_package(root, body)

        finished = run_rust_check(root, CONFIGURATION, "vulnerable-deps")

    is_unreachable = audit_error == UNREACHABLE_ERROR
    assert finished.returncode == int(not is_unreachable), finished.stderr
    assert ("unreachable" in finished.stderr) == is_unreachable


@HYPOTHESIS_SETTINGS
@given(advisory_ids)
def test_vulnerable_deps_property_passes_every_accepted_id_to_cargo_audit(
    whitelist: list[str],
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        calls = _stubbed_package(root, "exit 0\n")

        finished = run_rust_check(
            root, _whitelisted(whitelist), "vulnerable-deps"
        )
        recorded_calls = calls.read_text(encoding="utf-8")

    assert finished.returncode == 0, finished.stderr

    for advisory_id in whitelist:
        assert f"--ignore {advisory_id}" in recorded_calls


@HYPOTHESIS_SETTINGS
@given(st.booleans())
def test_vulnerable_deps_property_fails_on_a_reported_vulnerability(
    is_vulnerable: bool,
) -> None:
    report = here_document("REPORT", VULNERABLE_REPORT)
    summary = "error: 1 vulnerability found!\n"
    body = report + here_document("SUMMARY", summary) + "exit 1\n"

    if not is_vulnerable:
        body = "exit 0\n"

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        _ = _stubbed_package(root, body)

        finished = run_rust_check(root, CONFIGURATION, "vulnerable-deps")

    assert finished.returncode == int(is_vulnerable), finished.stderr
    assert ("RUSTSEC-2022-0013" in finished.stderr) == is_vulnerable


@HYPOTHESIS_SETTINGS
@given(member_counts)
def test_vulnerable_deps_property_audits_a_workspace_lockfile_once(
    member_count: int,
) -> None:
    member_names: list[str] = []
    listed_directories: list[str] = []

    for index in range(member_count):
        member_name = f"member{index}"
        member_names.append(member_name)
        listed_directories.append(f'"rust/crates/{member_name}/src"')

    listed_folders = ", ".join(listed_directories)
    configuration = f"source_directories = [{listed_folders}]\n"

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        repository(root)
        calls = _stub_audit(root, "exit 0\n")
        stage_file(root, "rust/Cargo.toml", WORKSPACE_MANIFEST)
        stage_file(root, "rust/Cargo.lock", _lockfile([]))

        for member_name in member_names:
            stage_file(
                root,
                f"rust/crates/{member_name}/Cargo.toml",
                package_manifest(member_name),
            )
            stage_file(root, f"rust/crates/{member_name}/src/lib.rs", "\n")

        finished = run_rust_check(root, configuration, "vulnerable-deps")
        recorded_calls = calls.read_text(encoding="utf-8").splitlines()

    assert finished.returncode == 0, finished.stderr
    assert len(recorded_calls) == 1
    assert "rust/Cargo.lock" in recorded_calls[0]


@HYPOTHESIS_SETTINGS
@given(st.from_regex(r"[a-z]{3,10}", fullmatch=True))
def test_vulnerable_deps_property_fails_fast_without_a_rust_lockfile(
    name_suffix: str,
) -> None:
    package = f"crate_{name_suffix}"

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        repository(root)
        _ = _stub_audit(root, "exit 0\n")
        stage_file(root, f"{package}/Cargo.toml", package_manifest(package))
        stage_file(root, f"{package}/src/lib.rs", "\n")

        configuration = f'source_directories = ["{package}/src"]\n'
        finished = run_rust_check(root, configuration, "vulnerable-deps")

    assert finished.returncode == 1
    assert f"{package}/Cargo.lock is missing" in finished.stderr
