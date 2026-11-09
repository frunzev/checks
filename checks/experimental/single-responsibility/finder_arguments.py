import argparse
from pathlib import Path

PERCENT = 100


class FinderArguments(argparse.Namespace):
    code_similarity: int = PERCENT
    models: Path = Path()
    cache: Path = Path()


def finder_argument_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    _ = parser.add_argument("--code-similarity", type=int, required=True)
    _ = parser.add_argument("--models", type=Path, required=True)
    _ = parser.add_argument("--cache", type=Path, required=True)

    return parser


def fraction_of(percent: int) -> float:
    return percent / PERCENT
