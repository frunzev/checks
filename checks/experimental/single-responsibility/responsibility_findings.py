import numpy

from code_embeddings import EmbeddingMatrix
from code_members import CodeMember, CodeUnit
from identifier_words import vocabulary_of
from responsibility_groups import (
    RelatednessThresholds,
    find_connected_groups,
    find_related_pairs,
    word_overlap_matrix,
)

type Responsibilities = tuple[tuple[CodeMember, ...], ...]

MINIMUM_GROUP_SIZE = 2
MINIMUM_RESPONSIBILITIES = 2
MINIMUM_SPLIT_MEMBERS = MINIMUM_GROUP_SIZE * MINIMUM_RESPONSIBILITIES
GROUP_SEPARATOR = " | "
NAME_SEPARATOR = ", "


def responsibility_members(unit: CodeUnit) -> tuple[CodeMember, ...]:
    members: list[CodeMember] = []

    for member in unit.members:
        if not member.is_constructor:
            members.append(member)

    return tuple(members)


def find_split_responsibilities(
    members: tuple[CodeMember, ...],
    member_vectors: EmbeddingMatrix,
    thresholds: RelatednessThresholds,
) -> Responsibilities:
    code_similarities = (member_vectors @ member_vectors.T).astype(
        numpy.float64
    )
    vocabularies = [vocabulary_of(member.identifiers) for member in members]
    word_overlaps = word_overlap_matrix(vocabularies)
    related_pairs = find_related_pairs(
        code_similarities, word_overlaps, thresholds
    )
    groups = find_connected_groups(len(members), related_pairs)
    responsibilities: list[tuple[CodeMember, ...]] = []

    for group in groups:
        if len(group) >= MINIMUM_GROUP_SIZE:
            responsibility = tuple(members[index] for index in group)
            responsibilities.append(responsibility)

    if len(responsibilities) < MINIMUM_RESPONSIBILITIES:
        return ()

    return tuple(responsibilities)


def describe_split_unit(
    unit: CodeUnit, responsibilities: Responsibilities
) -> str:
    listed_groups: list[str] = []

    for responsibility in responsibilities:
        names = [member.display_name for member in responsibility]
        listed_groups.append(NAME_SEPARATOR.join(names))

    return (
        f"{unit.path}:{unit.line}: {unit.title} has"
        f" {len(responsibilities)} responsibilities:"
        f" {GROUP_SEPARATOR.join(listed_groups)}"
    )


def describe_split_units(
    units: tuple[CodeUnit, ...],
    vectors_by_member: dict[CodeMember, EmbeddingMatrix],
    thresholds: RelatednessThresholds,
) -> list[str]:
    descriptions: list[str] = []

    for unit in units:
        members = responsibility_members(unit)

        if len(members) < MINIMUM_SPLIT_MEMBERS:
            continue

        member_vectors = numpy.array(
            [vectors_by_member[member] for member in members]
        )
        responsibilities = find_split_responsibilities(
            members, member_vectors, thresholds
        )

        if responsibilities:
            descriptions.append(describe_split_unit(unit, responsibilities))

    return descriptions
