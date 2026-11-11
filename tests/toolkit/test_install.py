import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from check_support import stub_code_model_downloader

TOOLKIT = Path(__file__).resolve().parents[2]
TOOLKIT_FOLDER = ".checks"
TOOLKIT_FILES = (
    "install.sh",
    "run",
    "tools.sh",
    "languages.sh",
    "dart_tools.sh",
    "rust_tools.sh",
)
TOOLKIT_FOLDERS = ("checks", "configuration", "hooks")
CONFIGURATION = (
    'source_directories = ["svc/src"]\n'
    'stable = "off"\n'
    "[checks.file-length]\n"
    'when = "pre-commit"\n'
    "max-lines = 3\n"
)
SUCCEEDING_STUB = "#!/bin/sh\nexit 0\n"
PINNED_RUST_TOOLS = (
    "cargo-machete@0.9.2",
    "cargo-audit@0.22.2",
    "cargo-llvm-cov@0.9.1",
)
RUST_COMPONENTS = ("clippy", "rustfmt", "llvm-tools-preview")
RUST_TOOL_ROOT = ".cargo-tools"
INSTALL_SETTINGS = settings(max_examples=3, deadline=None)


def _stub(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(SUCCEEDING_STUB, encoding="utf-8")
    path.chmod(0o755)


def _git(project: Path, *arguments: str) -> None:
    _ = subprocess.run(
        ["git", *arguments], cwd=project, check=True, capture_output=True
    )


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    toolkit = project / TOOLKIT_FOLDER
    toolkit.mkdir(parents=True)

    for file_name in TOOLKIT_FILES:
        _ = shutil.copy2(TOOLKIT / file_name, toolkit / file_name)

    for folder_name in TOOLKIT_FOLDERS:
        _ = shutil.copytree(
            TOOLKIT / folder_name,
            toolkit / folder_name,
            ignore=shutil.ignore_patterns("__pycache__"),
        )

    python_link = toolkit / ".venv" / "bin" / "python"
    python_link.parent.mkdir(parents=True)
    python_link.symlink_to(Path(sys.executable))
    _stub(toolkit / ".venv" / "bin" / "pip")
    stub_code_model_downloader(toolkit)
    _git(project, "init", "--quiet")
    _git(project, "config", "user.email", "hooks@example.com")
    _git(project, "config", "user.name", "hooks")

    return project


def _recording_stub(path: Path, calls: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    recorder = f'printf "%s\\n" "$*" >> "{calls}"\n'
    _ = path.write_text(f"#!/bin/sh\n{recorder}", encoding="utf-8")
    path.chmod(0o755)


def _stub_package_managers(shims: Path) -> None:
    _stub(shims / "npm")
    _stub(shims / "composer")
    _stub(shims / "dart")


def _run_install(
    project: Path, searched_folders: str
) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "PATH": searched_folders}

    return subprocess.run(
        ["sh", f"{TOOLKIT_FOLDER}/install.sh"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )


def _install(tmp_path: Path, project: Path) -> None:
    shims = tmp_path / "shims"
    _stub_package_managers(shims)
    _stub(shims / "cargo")
    _stub(shims / "rustup")

    _ = _run_install(project, f"{shims}:{os.environ['PATH']}")


def _install_recording_rust_calls(
    tmp_path: Path, rust_commands: tuple[str, ...]
) -> tuple[Path, str]:
    project = _project(tmp_path)
    shims = tmp_path / "shims"
    calls = tmp_path / "rust-calls"
    _stub_package_managers(shims)

    for rust_command in rust_commands:
        _recording_stub(shims / rust_command, calls)

    installed = _run_install(project, f"{shims}{os.pathsep}{os.defpath}")
    recorded_calls = ""

    if calls.exists():
        recorded_calls = calls.read_text(encoding="utf-8")

    return project, installed.stdout + recorded_calls


def test_install_keeps_a_last_ignore_line_without_a_newline(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)
    _ = (project / ".gitignore").write_text("node_modules", encoding="utf-8")

    _install(tmp_path, project)

    ignored = (project / ".gitignore").read_text(encoding="utf-8")
    assert ignored.splitlines() == ["node_modules", f"{TOOLKIT_FOLDER}/"]


def test_install_downloads_the_code_model_into_the_toolkit(
    tmp_path: Path,
) -> None:
    project = _project(tmp_path)

    _install(tmp_path, project)

    assert (project / TOOLKIT_FOLDER / ".models").is_dir()


def test_hooks_run_in_a_linked_worktree(tmp_path: Path) -> None:
    project = _project(tmp_path)
    _install(tmp_path, project)
    _ = (project / "checks.toml").write_text(CONFIGURATION, encoding="utf-8")
    (project / "svc" / "src").mkdir(parents=True)
    _ = (project / "svc" / "src" / "short.py").write_text(
        "VALUE = 1\n", encoding="utf-8"
    )
    _git(project, "add", ".")
    _git(project, "commit", "--quiet", "--message", "seed")
    worktree = tmp_path / "worktree"
    _git(project, "worktree", "add", "--quiet", str(worktree))
    _ = (worktree / "svc" / "src" / "long.py").write_text(
        "VALUE = 1\n" * 5, encoding="utf-8"
    )
    _git(worktree, "add", ".")

    committed = subprocess.run(
        ["git", "commit", "--quiet", "--message", "long"],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )

    assert committed.returncode != 0
    assert "svc/src/long.py" in committed.stdout + committed.stderr


@INSTALL_SETTINGS
@given(st.sampled_from(PINNED_RUST_TOOLS))
def test_install_property_installs_each_pinned_rust_tool_into_the_toolkit(
    pinned_tool: str,
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        project, output = _install_recording_rust_calls(
            Path(directory), ("cargo", "rustup")
        )
        tool_root = project.resolve() / TOOLKIT_FOLDER / RUST_TOOL_ROOT

    install_flags = f"install --quiet --locked --root {tool_root}"
    assert f"{install_flags} {pinned_tool}" in output.splitlines()


@INSTALL_SETTINGS
@given(st.sampled_from(RUST_COMPONENTS))
def test_install_property_adds_every_rust_component_through_rustup(
    component: str,
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        _, output = _install_recording_rust_calls(
            Path(directory), ("cargo", "rustup")
        )

    component_calls: list[str] = []

    for recorded_call in output.splitlines():
        if recorded_call.startswith("component add "):
            component_calls.append(recorded_call)

    assert len(component_calls) == 1
    assert component in component_calls[0].split()


@INSTALL_SETTINGS
@given(st.sampled_from([(), ("cargo",), ("rustup",)]))
def test_install_property_skips_rust_tools_without_cargo_and_rustup(
    rust_commands: tuple[str, ...],
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        _, output = _install_recording_rust_calls(
            Path(directory), rust_commands
        )

    assert "rust checks will not run" in output
    assert "install --" not in output
    assert "component add" not in output
