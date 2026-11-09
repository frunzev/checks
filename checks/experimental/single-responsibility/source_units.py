from pathlib import Path

from code_members import CodeUnit
from code_units import parse_code_units
from source_grammars import GRAMMARS_BY_SUFFIX, SourceGrammar


def grammar_for(source_path: Path) -> SourceGrammar:
    if source_path.suffix not in GRAMMARS_BY_SUFFIX:
        message = f"{source_path}: no grammar reads {source_path.suffix} files"
        raise ValueError(message)

    return GRAMMARS_BY_SUFFIX[source_path.suffix]


def source_paths_from(listing: str) -> list[Path]:
    source_paths: list[Path] = []

    for line in listing.split("\n"):
        if line:
            source_paths.append(Path(line))

    return source_paths


def read_code_units(source_paths: list[Path]) -> tuple[CodeUnit, ...]:
    units: list[CodeUnit] = []

    for source_path in source_paths:
        grammar = grammar_for(source_path)
        source = source_path.read_bytes()
        units.extend(parse_code_units(str(source_path), source, grammar))

    return tuple(units)
