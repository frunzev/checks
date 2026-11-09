import sys

from code_members import members_of
from repeated_dispatches import (
    describe_dispatch_place,
    find_repeated_dispatches,
)
from source_units import read_code_units, source_paths_from


def main() -> int:
    source_paths = source_paths_from(sys.stdin.read())
    members = members_of(read_code_units(source_paths))
    descriptions: list[str] = []

    for dispatch in find_repeated_dispatches(members):
        for place in dispatch.places:
            descriptions.append(describe_dispatch_place(place, dispatch))

    for description in sorted(descriptions):
        _ = sys.stdout.write(f"{description}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
