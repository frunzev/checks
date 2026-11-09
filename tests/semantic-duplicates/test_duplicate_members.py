import dataclasses

import numpy
from hypothesis import assume, given
from hypothesis import strategies as st

from code_embeddings import EmbeddingMatrix, normalize_rows
from code_members import CodeMember
from duplicate_members import (
    MINIMUM_DUPLICATE_LINES,
    describe_duplicate,
    duplicate_candidates,
    find_duplicate_members,
    find_similar_index_pairs,
    is_shared_interface_method,
)
from semantic_finder_support import code_member, member_names

VECTOR_SIZE = 3
THRESHOLD_MARGIN = 1e-4
similarities = st.floats(min_value=-1.0, max_value=1.0)
block_sizes = st.integers(min_value=1, max_value=4)
vector_rows = st.lists(
    st.lists(
        st.floats(min_value=0.125, max_value=1.0, width=32),
        min_size=VECTOR_SIZE,
        max_size=VECTOR_SIZE,
    ),
    max_size=7,
)
owner_names = st.none() | st.sampled_from(["Basket", "Ledger"])
languages = st.sampled_from(["python", "typescript"])
line_counts = st.integers(min_value=1, max_value=12)


@st.composite
def code_members(draw: st.DrawFn) -> list[CodeMember]:
    names = draw(st.lists(member_names, max_size=6))
    members: list[CodeMember] = []

    for position, name in enumerate(names):
        member = code_member(name, (), draw(owner_names), position + 1)
        member = dataclasses.replace(
            member, line_count=draw(line_counts), language=draw(languages)
        )
        members.append(member)

    return members


def _identical_vectors(member_count: int) -> EmbeddingMatrix:
    return numpy.ones((member_count, VECTOR_SIZE), dtype=numpy.float32)


@given(vector_rows, similarities, block_sizes)
def test_find_similar_index_pairs_property_matches_every_pair_comparison(
    rows: list[list[float]], minimum_similarity: float, block_rows: int
) -> None:
    vectors = normalize_rows(
        numpy.array(rows, dtype=numpy.float32).reshape(-1, VECTOR_SIZE)
    )
    all_similarities = vectors @ vectors.T
    distances_to_threshold = numpy.abs(
        all_similarities - minimum_similarity
    )
    assume(not numpy.any(distances_to_threshold < THRESHOLD_MARGIN))
    expected_pairs: list[tuple[int, int]] = []

    for first_index in range(len(vectors)):
        for second_index in range(first_index + 1, len(vectors)):
            similarity = all_similarities[first_index, second_index]

            if similarity >= minimum_similarity:
                expected_pairs.append((first_index, second_index))

    found_pairs = find_similar_index_pairs(
        vectors, minimum_similarity, block_rows
    )

    assert sorted(found_pairs) == expected_pairs


@given(code_members())
def test_duplicate_candidates_property_keeps_only_long_enough_members(
    members: list[CodeMember],
) -> None:
    candidates = duplicate_candidates(tuple(members))
    expected_candidates = [
        member
        for member in members
        if member.line_count >= MINIMUM_DUPLICATE_LINES
    ]

    assert list(candidates) == expected_candidates


@given(member_names, member_names, owner_names, owner_names)
def test_is_shared_interface_method_property_needs_two_methods_of_one_name(
    first_name: str,
    second_name: str,
    first_owner: str | None,
    second_owner: str | None,
) -> None:
    first_member = code_member(first_name, (), first_owner, 1)
    second_member = code_member(second_name, (), second_owner, 2)
    are_methods = first_owner is not None and second_owner is not None

    is_shared = is_shared_interface_method(first_member, second_member)

    assert is_shared == (are_methods and first_name == second_name)


@given(code_members(), block_sizes)
def test_find_duplicate_members_property_reports_both_directions(
    members: list[CodeMember], block_rows: int
) -> None:
    vectors = _identical_vectors(len(members))

    vectors_by_member = dict(zip(members, vectors, strict=True))

    duplicates = find_duplicate_members(
        vectors_by_member, 0.9, block_rows
    )

    for member, other_member in duplicates:
        assert (other_member, member) in duplicates


@given(code_members(), block_sizes)
def test_find_duplicate_members_property_pairs_every_identical_candidate(
    members: list[CodeMember], block_rows: int
) -> None:
    vectors = _identical_vectors(len(members))

    vectors_by_member = dict(zip(members, vectors, strict=True))

    duplicates = find_duplicate_members(
        vectors_by_member, 0.9, block_rows
    )
    candidates = duplicate_candidates(tuple(members))
    expected_pairs = [
        (member, other_member)
        for member in candidates
        for other_member in candidates
        if member != other_member
        and member.language == other_member.language
        and not is_shared_interface_method(member, other_member)
    ]

    assert sorted(duplicates, key=str) == sorted(expected_pairs, key=str)


@given(code_members(), block_sizes)
def test_find_duplicate_members_property_never_pairs_dissimilar_members(
    members: list[CodeMember], block_rows: int
) -> None:
    vectors = numpy.eye(max(len(members), 1), dtype=numpy.float32)
    vectors = vectors[: len(members)]

    vectors_by_member = dict(zip(members, vectors, strict=True))

    duplicates = find_duplicate_members(
        vectors_by_member, 0.5, block_rows
    )

    assert duplicates == []


@given(member_names, member_names, owner_names, owner_names)
def test_describe_duplicate_property_names_both_members_and_places(
    first_name: str,
    second_name: str,
    first_owner: str | None,
    second_owner: str | None,
) -> None:
    first_member = code_member(first_name, (), first_owner, 3)
    second_member = code_member(second_name, (), second_owner, 9)

    description = describe_duplicate(first_member, second_member)

    assert description == (
        f"{first_member.path}:3: {first_member.display_name} duplicates "
        f"{second_member.path}:9: {second_member.display_name}"
    )
