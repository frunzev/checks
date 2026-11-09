import dataclasses

import numpy
from hypothesis import given
from hypothesis import strategies as st

from code_embeddings import EmbeddingMatrix
from code_members import CodeMember, CodeUnit, members_of
from responsibility_findings import (
    describe_split_unit,
    describe_split_units,
    find_split_responsibilities,
    responsibility_members,
)
from responsibility_groups import RelatednessThresholds
from semantic_finder_support import code_member, code_unit, member_names

FIRST_SUBJECT = ("invoice_total", "tax_rate")
SECOND_SUBJECT = ("email_sender", "smtp_host")
VECTOR_SIZE = 2
FIRST_DIRECTION = (1.0, 0.0)
SECOND_DIRECTION = (0.0, 1.0)
group_sizes = st.integers(min_value=2, max_value=4)
positive_scores = st.floats(min_value=0.01, max_value=1.0)
thresholds = st.builds(
    RelatednessThresholds,
    code_similarity=positive_scores,
    word_overlap=positive_scores,
)


def _subject_members(
    prefix: str, identifiers: tuple[str, ...], count: int, first_line: int
) -> list[CodeMember]:
    members: list[CodeMember] = []

    for position in range(count):
        members.append(
            code_member(
                name=f"{prefix}_{position}",
                identifiers=identifiers,
                owner_name="Holder",
                line=first_line + position,
            )
        )

    return members


def _two_subjects(
    first_count: int, second_count: int
) -> tuple[list[CodeMember], list[CodeMember], EmbeddingMatrix]:
    first_members = _subject_members("bill", FIRST_SUBJECT, first_count, 1)
    second_members = _subject_members(
        "mail", SECOND_SUBJECT, second_count, first_count + 1
    )
    directions = [FIRST_DIRECTION] * first_count
    directions += [SECOND_DIRECTION] * second_count
    vectors = numpy.array(directions, dtype=numpy.float32)

    return first_members, second_members, vectors


@given(group_sizes, group_sizes, thresholds)
def test_find_split_responsibilities_property_separates_unrelated_subjects(
    first_count: int,
    second_count: int,
    chosen_thresholds: RelatednessThresholds,
) -> None:
    first_members, second_members, vectors = _two_subjects(
        first_count, second_count
    )
    members = tuple(first_members + second_members)

    responsibilities = find_split_responsibilities(
        members, vectors, chosen_thresholds
    )

    assert responsibilities == (tuple(first_members), tuple(second_members))


@given(group_sizes, group_sizes, thresholds)
def test_find_split_responsibilities_property_keeps_similar_code_together(
    first_count: int,
    second_count: int,
    chosen_thresholds: RelatednessThresholds,
) -> None:
    first_members, second_members, _ = _two_subjects(first_count, second_count)
    members = tuple(first_members + second_members)
    same_direction = [FIRST_DIRECTION] * len(members)
    vectors = numpy.array(same_direction, dtype=numpy.float32)

    responsibilities = find_split_responsibilities(
        members, vectors, chosen_thresholds
    )

    assert responsibilities == ()


@given(group_sizes, thresholds)
def test_find_split_responsibilities_property_ignores_a_lone_member(
    first_count: int, chosen_thresholds: RelatednessThresholds
) -> None:
    first_members, second_members, vectors = _two_subjects(first_count, 1)
    members = tuple(first_members + second_members)

    responsibilities = find_split_responsibilities(
        members, vectors, chosen_thresholds
    )

    assert responsibilities == ()


@given(st.lists(st.booleans(), max_size=6))
def test_responsibility_members_property_leaves_out_only_constructors(
    constructor_flags: list[bool],
) -> None:
    members: list[CodeMember] = []

    for position, is_constructor in enumerate(constructor_flags):
        member = code_member(f"run_{position}", (), "Holder", position + 1)
        member = dataclasses.replace(member, is_constructor=is_constructor)
        members.append(member)

    kept_members = responsibility_members(code_unit(tuple(members)))
    expected_members = [
        member for member in members if not member.is_constructor
    ]

    assert list(kept_members) == expected_members


@given(st.lists(st.lists(member_names, min_size=2, max_size=3), min_size=2))
def test_describe_split_unit_property_lists_every_responsibility(
    grouped_names: list[list[str]],
) -> None:
    responsibilities: list[tuple[CodeMember, ...]] = []

    for names in grouped_names:
        group = [code_member(name, (), "Holder", 1) for name in names]
        responsibilities.append(tuple(group))

    unit = code_unit(())
    description = describe_split_unit(unit, tuple(responsibilities))
    prefix = (
        f"{unit.path}:{unit.line}: {unit.title} has "
        f"{len(grouped_names)} responsibilities: "
    )
    listed_groups = description.removeprefix(prefix).split(" | ")
    listed_names = [group.split(", ") for group in listed_groups]
    expected_names = [
        [f"Holder.{name}" for name in names] for names in grouped_names
    ]

    assert description.startswith(prefix)
    assert listed_names == expected_names


@given(group_sizes, group_sizes, thresholds)
def test_describe_split_units_property_reports_only_split_units(
    first_count: int,
    second_count: int,
    chosen_thresholds: RelatednessThresholds,
) -> None:
    first_members, second_members, vectors = _two_subjects(
        first_count, second_count
    )
    split_unit = code_unit(tuple(first_members + second_members))
    cohesive_unit = dataclasses.replace(
        code_unit(tuple(first_members)), title="class Cohesive"
    )
    vectors_by_member: dict[CodeMember, EmbeddingMatrix] = {}

    for member, vector in zip(split_unit.members, vectors, strict=True):
        vectors_by_member[member] = vector

    descriptions = describe_split_units(
        (split_unit, cohesive_unit), vectors_by_member, chosen_thresholds
    )

    assert len(descriptions) == 1
    assert descriptions[0].startswith(f"{split_unit.path}:1: class Holder ")


@given(st.lists(st.lists(member_names, max_size=3), max_size=4))
def test_members_of_property_keeps_every_member_in_unit_order(
    grouped_names: list[list[str]],
) -> None:
    units: list[CodeUnit] = []
    expected_members: list[CodeMember] = []

    for names in grouped_names:
        members = tuple(code_member(name, (), None, 1) for name in names)
        units.append(code_unit(members))
        expected_members.extend(members)

    assert members_of(tuple(units)) == tuple(expected_members)
