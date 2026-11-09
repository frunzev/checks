import sys

from duplicate_members import describe_duplicate, find_duplicate_members
from finder_arguments import (
    FinderArguments,
    finder_argument_parser,
    fraction_of,
)
from member_embeddings import embed_unit_members
from source_units import read_code_units, source_paths_from

DESCRIPTION = "Report functions that repeat another function in other words."
SIMILARITY_BLOCK_ROWS = 1024


def main() -> int:
    parser = finder_argument_parser(DESCRIPTION)
    arguments = parser.parse_args(namespace=FinderArguments())
    source_paths = source_paths_from(sys.stdin.read())
    units = read_code_units(source_paths)
    vectors_by_member = embed_unit_members(
        units, arguments.models, arguments.cache
    )
    duplicates = find_duplicate_members(
        vectors_by_member,
        fraction_of(arguments.code_similarity),
        SIMILARITY_BLOCK_ROWS,
    )
    descriptions: list[str] = []

    for member, other_member in duplicates:
        descriptions.append(describe_duplicate(member, other_member))

    for description in sorted(descriptions):
        _ = sys.stdout.write(f"{description}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
