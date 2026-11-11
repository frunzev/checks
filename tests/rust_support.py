import os
import shutil
import subprocess
from pathlib import Path

from check_support import (
    COPIED_TOOLKIT,
    TOOLKIT,
    CheckRun,
    repository,
    stage_file,
)

RUST_PACKAGE = "app"
RUST_LIBRARY = "app/src/lib.rs"
RUST_CONFIGURATION = 'source_directories = ["app/src", "app/tests"]\n'
RUST_TOOL_ROOT = ".cargo-tools"
WORKSPACE_MANIFEST = '[workspace]\nresolver = "3"\nmembers = ["crates/*"]\n'


def package_manifest(name: str) -> str:
    return (
        f'[package]\nname = "{name}"\nversion = "0.1.0"\nedition = "2024"\n'
    )


RUST_MANIFEST = package_manifest(RUST_PACKAGE)


def _cargo_folder() -> Path:
    cargo_on_path = shutil.which("cargo")

    if cargo_on_path is not None:
        return Path(cargo_on_path).parent

    located_cargo = subprocess.run(
        ["rustup", "which", "cargo"],
        capture_output=True,
        text=True,
        check=True,
    )

    return Path(located_cargo.stdout.strip()).parent


def rust_environment() -> dict[str, str]:
    searched_folders = f"{_cargo_folder()}{os.pathsep}{os.environ['PATH']}"

    return {**os.environ, "PATH": searched_folders}


def link_toolkit_rust_tools(tmp_path: Path) -> None:
    copied_tools = tmp_path / COPIED_TOOLKIT / RUST_TOOL_ROOT
    copied_tools.symlink_to(TOOLKIT / RUST_TOOL_ROOT)


def rust_package(tmp_path: Path, manifest: str) -> None:
    repository(tmp_path)
    link_toolkit_rust_tools(tmp_path)
    stage_file(tmp_path, f"{RUST_PACKAGE}/Cargo.toml", manifest)


def rust_workspace(tmp_path: Path, member_names: list[str]) -> None:
    repository(tmp_path)
    link_toolkit_rust_tools(tmp_path)
    stage_file(tmp_path, "rust/Cargo.toml", WORKSPACE_MANIFEST)

    for member_name in member_names:
        stage_file(
            tmp_path,
            f"rust/crates/{member_name}/Cargo.toml",
            package_manifest(member_name),
        )


def run_rust_check(
    tmp_path: Path, configuration: str, name: str
) -> CheckRun:
    _ = (tmp_path / "checks.toml").write_text(configuration, encoding="utf-8")

    return subprocess.run(
        ["sh", f"{COPIED_TOOLKIT}/run", name],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=rust_environment(),
    )
