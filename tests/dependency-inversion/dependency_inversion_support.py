import keyword
import sys
import tempfile
from pathlib import Path

from hypothesis import strategies as st

from typescript_finder_support import CHECKS

FINDER_DIRECTORY = CHECKS / "experimental" / "dependency-inversion" / "python"
IDENTIFIERS = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz", min_size=3, max_size=7
).filter(lambda name: not keyword.iskeyword(name))

if str(FINDER_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(FINDER_DIRECTORY))

from collaborator_classes import collaborator_names, wires_dependencies
from constructed_collaborators import constructed_collaborators
from dependency_inversion_findings import (
    ConstructedCollaborator,
    message_for,
)

__all__ = [
    "IDENTIFIERS",
    "ConstructedCollaborator",
    "collaborator_names",
    "findings_for",
    "message_for",
    "repository_module",
    "service_owning",
    "wires_dependencies",
    "written_paths",
]


def written_paths(root: Path, modules: dict[str, str]) -> list[str]:
    paths: list[str] = []

    for name, source in modules.items():
        module = root / name
        module.parent.mkdir(parents=True, exist_ok=True)
        _ = module.write_text(source, encoding="utf-8")
        paths.append(str(module))

    return paths


def findings_for(modules: dict[str, str]) -> list[str]:
    with tempfile.TemporaryDirectory() as directory:
        paths = written_paths(Path(directory), modules)

        return [
            f"{Path(finding.path).name}:{finding.line_number}: "
            f"{message_for(finding)}"
            for finding in constructed_collaborators(paths)
        ]


def repository_module(name: str = "SqlUnitRepository") -> str:
    return (
        f"class {name}:\n"
        "    def fetch(self, unit_id):\n        return unit_id\n"
    )


def service_owning(owner: str, constructions: list[str]) -> str:
    assignments = "".join(
        f"        self.dependency_{index} = {construction}()\n"
        for index, construction in enumerate(constructions)
    )

    return (
        f"class {owner}:\n"
        "    def __init__(self):\n"
        f"{assignments}"
        "    def run(self):\n        return None\n"
    )
