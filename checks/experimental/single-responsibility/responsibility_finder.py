import sys

from finder_arguments import (
    FinderArguments,
    finder_argument_parser,
    fraction_of,
)
from member_embeddings import embed_unit_members
from responsibility_findings import describe_split_units
from responsibility_groups import RelatednessThresholds
from source_units import read_code_units, source_paths_from

DESCRIPTION = "Report classes and modules holding unrelated responsibilities."


class ResponsibilityFinderArguments(FinderArguments):
    word_overlap: int = 0


def main() -> int:
    parser = finder_argument_parser(DESCRIPTION)
    _ = parser.add_argument("--word-overlap", type=int, required=True)
    arguments = parser.parse_args(namespace=ResponsibilityFinderArguments())
    source_paths = source_paths_from(sys.stdin.read())
    units = read_code_units(source_paths)
    vectors_by_member = embed_unit_members(
        units, arguments.models, arguments.cache
    )
    thresholds = RelatednessThresholds(
        code_similarity=fraction_of(arguments.code_similarity),
        word_overlap=fraction_of(arguments.word_overlap),
    )

    for description in describe_split_units(
        units, vectors_by_member, thresholds
    ):
        _ = sys.stdout.write(f"{description}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
