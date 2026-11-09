import numpy

from code_embeddings import EmbeddingMatrix
from code_members import CodeMember

type DuplicatePair = tuple[CodeMember, CodeMember]

MINIMUM_DUPLICATE_LINES = 5


def duplicate_candidates(
    members: tuple[CodeMember, ...],
) -> tuple[CodeMember, ...]:
    candidates: list[CodeMember] = []

    for member in members:
        if member.line_count >= MINIMUM_DUPLICATE_LINES:
            candidates.append(member)

    return tuple(candidates)


def find_similar_index_pairs(
    vectors: EmbeddingMatrix, minimum_similarity: float, block_rows: int
) -> list[tuple[int, int]]:
    similar_pairs: list[tuple[int, int]] = []

    for block_start in range(0, len(vectors), block_rows):
        block_vectors = vectors[block_start : block_start + block_rows]
        block_similarities = block_vectors @ vectors.T
        is_similar = block_similarities >= minimum_similarity
        block_indexes, other_indexes = numpy.nonzero(is_similar)

        for block_index, other_index in zip(
            block_indexes.tolist(), other_indexes.tolist(), strict=True
        ):
            first_index = block_start + block_index

            if first_index < other_index:
                similar_pairs.append((first_index, other_index))

    return similar_pairs


def is_shared_interface_method(
    member: CodeMember, other_member: CodeMember
) -> bool:
    is_method = member.owner_name is not None
    is_other_method = other_member.owner_name is not None
    is_same_name = member.name == other_member.name

    return is_method and is_other_method and is_same_name


def find_duplicate_members(
    vectors_by_member: dict[CodeMember, EmbeddingMatrix],
    minimum_similarity: float,
    block_rows: int,
) -> list[DuplicatePair]:
    candidates = duplicate_candidates(tuple(vectors_by_member))
    candidate_vectors = numpy.array(
        [vectors_by_member[candidate] for candidate in candidates]
    )
    duplicates: list[DuplicatePair] = []

    for first_index, second_index in find_similar_index_pairs(
        candidate_vectors, minimum_similarity, block_rows
    ):
        member = candidates[first_index]
        other_member = candidates[second_index]

        if member.language != other_member.language:
            continue

        if is_shared_interface_method(member, other_member):
            continue

        duplicates.append((member, other_member))
        duplicates.append((other_member, member))

    return duplicates


def describe_duplicate(member: CodeMember, other_member: CodeMember) -> str:
    return (
        f"{member.path}:{member.line}: {member.display_name} duplicates"
        f" {other_member.path}:{other_member.line}:"
        f" {other_member.display_name}"
    )
