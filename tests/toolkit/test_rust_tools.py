import os
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from check_support import here_document
from shell_support import printed_lines, shell_function

SHELL_SETTINGS = settings(max_examples=25, deadline=None)
MINIMUM_MINOR_VERSION = 97
INSTALL_HINT = "cargo is not installed"
TOO_OLD_HINT = f"need cargo 1.{MINIMUM_MINOR_VERSION} or newer"
minor_versions = st.integers(min_value=0, max_value=300)
patch_versions = st.integers(min_value=0, max_value=30)
version_noise = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789.- ()", max_size=30
).filter(lambda line: not line.startswith("cargo 1."))
folder_names = st.from_regex(r"[a-z][a-z0-9_-]{0,10}", fullmatch=True)
file_stems = st.from_regex(r"[a-z][a-z0-9_]{0,10}", fullmatch=True)
other_extensions = st.sampled_from(["py", "rsx", "rs.bak", "toml", "txt"])


def _with_cargo_printing(folder: Path, version_line: str) -> dict[str, str]:
    stub = folder / "stubs" / "cargo"
    stub.parent.mkdir(parents=True)
    version_printer = here_document("VERSION", f"{version_line}\n")
    _ = stub.write_text(f"#!/bin/sh\n{version_printer}", encoding="utf-8")
    stub.chmod(0o755)

    return {"PATH": f"{stub.parent}{os.pathsep}{os.defpath}"}


def _require_cargo(version_line: str) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        environment = _with_cargo_printing(folder, version_line)

        finished = shell_function(folder, "require_cargo", environment)

    return finished.returncode, finished.stderr


@SHELL_SETTINGS
@given(minor_versions, patch_versions)
def test_require_cargo_property_accepts_exactly_the_supported_versions(
    minor_version: int, patch_version: int
) -> None:
    version_line = f"cargo 1.{minor_version}.{patch_version} (5f94df478)"

    returncode, errors = _require_cargo(version_line)

    is_supported = minor_version >= MINIMUM_MINOR_VERSION
    assert returncode == int(not is_supported), errors
    assert (TOO_OLD_HINT in errors) == (not is_supported)


@SHELL_SETTINGS
@given(version_noise)
def test_require_cargo_property_rejects_a_version_it_cannot_read(
    version_line: str,
) -> None:
    returncode, errors = _require_cargo(version_line)

    assert returncode == 1
    assert TOO_OLD_HINT in errors


@SHELL_SETTINGS
@given(minor_versions.filter(lambda minor: minor < MINIMUM_MINOR_VERSION))
def test_require_cargo_property_names_the_version_it_rejects(
    minor_version: int,
) -> None:
    version_line = f"cargo 1.{minor_version}.0 (5f94df478 2026-01-01)"

    returncode, errors = _require_cargo(version_line)

    assert returncode == 1
    assert version_line in errors


@SHELL_SETTINGS
@given(folder_names)
def test_require_cargo_property_fails_fast_without_cargo(
    folder_name: str,
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        empty_folder = folder / folder_name
        empty_folder.mkdir()
        environment = {"PATH": f"{empty_folder}{os.pathsep}{os.defpath}"}

        finished = shell_function(folder, "require_cargo", environment)

    assert finished.returncode == 1
    assert INSTALL_HINT in finished.stderr


def _require_rust_package(
    package: str, manifest_kind: str
) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as directory:
        project_root = Path(directory)
        manifest = project_root / package / "Cargo.toml"
        manifest.parent.mkdir(parents=True)

        if manifest_kind == "file":
            _ = manifest.write_text("[package]\n", encoding="utf-8")

        if manifest_kind == "folder":
            manifest.mkdir()

        finished = shell_function(
            project_root, f'require_rust_package "{package}"', {}
        )

    return finished.returncode, finished.stderr


@SHELL_SETTINGS
@given(st.lists(folder_names, min_size=1, max_size=3), st.booleans())
def test_require_rust_package_property_passes_only_beside_a_manifest(
    folders: list[str], has_manifest: bool
) -> None:
    package = "/".join(folders)
    manifest_kind = "file" if has_manifest else "none"

    returncode, errors = _require_rust_package(package, manifest_kind)

    assert returncode == int(not has_manifest), errors


@SHELL_SETTINGS
@given(st.lists(folder_names, min_size=1, max_size=3))
def test_require_rust_package_property_names_the_package_it_rejects(
    folders: list[str],
) -> None:
    package = "/".join(folders)

    returncode, errors = _require_rust_package(package, "none")

    assert returncode == 1
    assert f"{package} has no Cargo.toml" in errors


@SHELL_SETTINGS
@given(st.lists(folder_names, min_size=1, max_size=3))
def test_require_rust_package_property_rejects_a_manifest_folder(
    folders: list[str],
) -> None:
    package = "/".join(folders)

    returncode, errors = _require_rust_package(package, "folder")

    assert returncode == 1, errors


def _rust_files(project_root: Path, folders: list[str]) -> list[str]:
    quoted_folders: list[str] = []

    for folder in folders:
        quoted_folders.append(f'"{folder}"')

    listed_folders = " ".join(quoted_folders)
    finished = shell_function(
        project_root, f"rust_files_in {listed_folders}", {}
    )

    return printed_lines(finished)


def _write_file(project_root: Path, relative: str) -> None:
    path = project_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text("", encoding="utf-8")


@SHELL_SETTINGS
@given(
    st.lists(file_stems, min_size=1, max_size=5, unique=True),
    st.lists(st.tuples(file_stems, other_extensions), max_size=5),
)
def test_rust_files_in_property_lists_exactly_the_rust_files(
    rust_stems: list[str], other_files: list[tuple[str, str]]
) -> None:
    expected_files: list[str] = []

    with tempfile.TemporaryDirectory() as directory:
        project_root = Path(directory)

        for stem in rust_stems:
            relative = f"crate/src/{stem}.rs"
            _write_file(project_root, relative)
            expected_files.append(relative)

        for stem, extension in other_files:
            _write_file(project_root, f"crate/src/{stem}.{extension}")

        listed_files = _rust_files(project_root, ["crate/src"])

    assert listed_files == sorted(expected_files)


@SHELL_SETTINGS
@given(st.lists(folder_names, min_size=1, max_size=4), file_stems)
def test_rust_files_in_property_finds_a_module_at_any_depth(
    folders: list[str], stem: str
) -> None:
    relative = "crate/src/" + "/".join(folders) + f"/{stem}.rs"

    with tempfile.TemporaryDirectory() as directory:
        project_root = Path(directory)
        _write_file(project_root, relative)

        listed_files = _rust_files(project_root, ["crate/src"])

    assert listed_files == [relative]


@SHELL_SETTINGS
@given(folder_names, file_stems)
def test_rust_files_in_property_lists_a_file_once_in_overlapping_folders(
    folder: str, stem: str
) -> None:
    relative = f"crate/src/{folder}/{stem}.rs"

    with tempfile.TemporaryDirectory() as directory:
        project_root = Path(directory)
        _write_file(project_root, relative)

        listed_files = _rust_files(
            project_root, ["crate/src", f"crate/src/{folder}"]
        )

    assert listed_files == [relative]
