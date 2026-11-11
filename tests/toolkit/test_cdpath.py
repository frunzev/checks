import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from hypothesis import example, given, settings
from hypothesis import strategies as st

from check_support import TOOLKIT, stub_code_model_downloader

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
    "[checks.strict-typing]\n"
    'when = "pre-commit"\n'
)
CDPATHS = (".:{elsewhere}", "{elsewhere}:.", "{elsewhere}", "{project}", ".")
VENV_SHIM = (
    "#!/bin/sh\n"
    'mkdir -p "$3/bin"\n'
    "printf '#!/bin/sh\\nexit 0\\n' > \"$3/bin/pip\"\n"
    'chmod +x "$3/bin/pip"\n'
)


def _executable(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def _link(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)


def _git(project: Path, *arguments: str) -> None:
    _ = subprocess.run(
        ["git", *arguments], cwd=project, check=True, capture_output=True
    )


def _project(workspace: Path) -> Path:
    project = workspace / "project"
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

    tools = toolkit / ".venv" / "bin"
    _link(tools / "python", Path(sys.executable))
    _link(tools / "basedpyright", TOOLKIT / ".venv" / "bin" / "basedpyright")
    _executable(tools / "pip", "#!/bin/sh\nexit 0\n")
    stub_code_model_downloader(toolkit)
    _link(project / ".venv" / "bin" / "python", Path(sys.executable))
    _ = (project / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    _ = (project / "checks.toml").write_text(CONFIGURATION, encoding="utf-8")
    source = project / "svc" / "src" / "value.py"
    source.parent.mkdir(parents=True)
    _ = source.write_text('VALUE: int = "a"\n', encoding="utf-8")
    _git(project, "init", "--quiet")
    _git(project, "config", "user.email", "hooks@example.com")
    _git(project, "config", "user.name", "hooks")

    return project


def _environment(workspace: Path, cdpath: str) -> dict[str, str]:
    shims = workspace / "shims"
    _executable(shims / "npm", "#!/bin/sh\nexit 0\n")
    _executable(shims / "composer", "#!/bin/sh\nexit 0\n")
    _executable(shims / "dart", "#!/bin/sh\nexit 0\n")
    _executable(shims / "cargo", "#!/bin/sh\nexit 0\n")
    _executable(shims / "rustup", "#!/bin/sh\nexit 0\n")
    _executable(shims / "python3", VENV_SHIM)
    elsewhere = workspace / "elsewhere"
    project = workspace / "project"

    return {
        **os.environ,
        "PATH": f"{shims}:{os.environ['PATH']}",
        "CDPATH": cdpath.format(elsewhere=elsewhere, project=project),
    }


@given(cdpath=st.sampled_from(CDPATHS))
@example(cdpath=".:{elsewhere}")
@example(cdpath="{elsewhere}")
@settings(max_examples=2, deadline=None)
def test_hook_property_rejects_a_type_error_under_any_cdpath(
    cdpath: str,
) -> None:
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory)
        clean = workspace / "elsewhere" / "svc" / "src" / "value.py"
        clean.parent.mkdir(parents=True)
        _ = clean.write_text("VALUE: int = 1\n", encoding="utf-8")
        project = _project(workspace)
        environment = _environment(workspace, cdpath)
        _ = subprocess.run(
            ["sh", f"{TOOLKIT_FOLDER}/install.sh"],
            cwd=project,
            check=True,
            capture_output=True,
            env=environment,
        )
        _git(project, "add", "-A")
        committed = subprocess.run(
            ["git", "commit", "--quiet", "-m", "type error"],
            cwd=project,
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )

    assert committed.returncode != 0
    assert "svc does not type-check" in committed.stderr
