from dataclasses import dataclass
from typing import cast

import numpy
from numpy.typing import NDArray

from set_overlap import overlap_of

type ScoreMatrix = NDArray[numpy.float64]
type MemberGroups = tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class RelatednessThresholds:
    code_similarity: float
    word_overlap: float


def word_overlap_matrix(vocabularies: list[frozenset[str]]) -> ScoreMatrix:
    member_count = len(vocabularies)
    overlaps = numpy.zeros((member_count, member_count))

    for first_index, first_vocabulary in enumerate(vocabularies):
        for second_index, second_vocabulary in enumerate(vocabularies):
            overlaps[first_index, second_index] = overlap_of(
                first_vocabulary, second_vocabulary
            )

    return overlaps


def find_related_pairs(
    code_similarities: ScoreMatrix,
    word_overlaps: ScoreMatrix,
    thresholds: RelatednessThresholds,
) -> frozenset[tuple[int, int]]:
    related_pairs: set[tuple[int, int]] = set()
    member_count = len(code_similarities)
    similarity_rows = cast("list[list[float]]", code_similarities.tolist())
    overlap_rows = cast("list[list[float]]", word_overlaps.tolist())

    for first_index in range(member_count):
        for second_index in range(first_index + 1, member_count):
            code_similarity = similarity_rows[first_index][second_index]
            shared_words = overlap_rows[first_index][second_index]
            is_similar_code = code_similarity >= thresholds.code_similarity
            is_shared_vocabulary = shared_words >= thresholds.word_overlap

            if is_similar_code or is_shared_vocabulary:
                related_pairs.add((first_index, second_index))

    return frozenset(related_pairs)


def find_connected_groups(
    member_count: int, related_pairs: frozenset[tuple[int, int]]
) -> MemberGroups:
    partners: dict[int, set[int]] = {}

    for index in range(member_count):
        partners[index] = set()

    for first_index, second_index in related_pairs:
        partners[first_index].add(second_index)
        partners[second_index].add(first_index)

    grouped_members: set[int] = set()
    groups: list[tuple[int, ...]] = []

    for start_index in range(member_count):
        if start_index in grouped_members:
            continue

        group = _members_reachable_from(start_index, partners)
        grouped_members.update(group)
        groups.append(tuple(sorted(group)))

    return tuple(groups)


def _members_reachable_from(
    start_index: int, partners: dict[int, set[int]]
) -> set[int]:
    reached_members = {start_index}
    pending_members = [start_index]

    while pending_members:
        member_index = pending_members.pop()

        for partner_index in partners[member_index]:
            if partner_index not in reached_members:
                reached_members.add(partner_index)
                pending_members.append(partner_index)

    return reached_members
