import numpy
from hypothesis import given
from hypothesis import strategies as st

from responsibility_groups import (
    RelatednessThresholds,
    ScoreMatrix,
    find_connected_groups,
    find_related_pairs,
    word_overlap_matrix,
)
from semantic_finder_support import lowercase_words
from set_overlap import overlap_of

MAXIMUM_MEMBERS = 7
scores = st.floats(min_value=0.0, max_value=1.0)
thresholds = st.builds(
    RelatednessThresholds, code_similarity=scores, word_overlap=scores
)
vocabulary_lists = st.lists(
    st.frozensets(lowercase_words, max_size=4), max_size=MAXIMUM_MEMBERS
)


@st.composite
def related_member_graphs(
    draw: st.DrawFn,
) -> tuple[int, frozenset[tuple[int, int]]]:
    member_count = draw(st.integers(min_value=0, max_value=MAXIMUM_MEMBERS))
    possible_pairs: list[tuple[int, int]] = []

    for first_index in range(member_count):
        for second_index in range(first_index + 1, member_count):
            possible_pairs.append((first_index, second_index))

    if not possible_pairs:
        return member_count, frozenset()

    related_pairs = draw(st.frozensets(st.sampled_from(possible_pairs)))

    return member_count, related_pairs


@st.composite
def symmetric_score_matrices(
    draw: st.DrawFn, member_count: int
) -> ScoreMatrix:
    matrix = numpy.ones((member_count, member_count))

    for first_index in range(member_count):
        for second_index in range(first_index + 1, member_count):
            score = draw(scores)
            matrix[first_index, second_index] = score
            matrix[second_index, first_index] = score

    return matrix


def _group_of(groups: tuple[tuple[int, ...], ...], index: int) -> int:
    for group_position, group in enumerate(groups):
        if index in group:
            return group_position

    message = f"{index} is in no group"
    raise AssertionError(message)


@given(related_member_graphs())
def test_find_connected_groups_property_places_every_member_once(
    graph: tuple[int, frozenset[tuple[int, int]]],
) -> None:
    member_count, related_pairs = graph

    groups = find_connected_groups(member_count, related_pairs)
    grouped_members = [index for group in groups for index in group]

    assert sorted(grouped_members) == list(range(member_count))


@given(related_member_graphs())
def test_find_connected_groups_property_keeps_related_members_together(
    graph: tuple[int, frozenset[tuple[int, int]]],
) -> None:
    member_count, related_pairs = graph

    groups = find_connected_groups(member_count, related_pairs)

    for first_index, second_index in related_pairs:
        assert _group_of(groups, first_index) == _group_of(groups, second_index)


@given(related_member_graphs())
def test_find_connected_groups_property_never_joins_an_unrelated_member(
    graph: tuple[int, frozenset[tuple[int, int]]],
) -> None:
    member_count, related_pairs = graph

    groups = find_connected_groups(member_count, related_pairs)

    for group in groups:
        if len(group) == 1:
            continue

        for index in group:
            partners = [
                pair for pair in related_pairs if index in pair
            ]
            assert partners


@given(related_member_graphs())
def test_find_connected_groups_property_orders_groups_by_first_member(
    graph: tuple[int, frozenset[tuple[int, int]]],
) -> None:
    member_count, related_pairs = graph

    groups = find_connected_groups(member_count, related_pairs)
    first_members = [group[0] for group in groups]

    assert first_members == sorted(first_members)

    for group in groups:
        assert list(group) == sorted(group)


@given(st.data(), st.integers(min_value=0, max_value=MAXIMUM_MEMBERS))
def test_find_related_pairs_property_relates_members_above_either_threshold(
    data: st.DataObject, member_count: int
) -> None:
    code_similarities = data.draw(symmetric_score_matrices(member_count))
    word_overlaps = data.draw(symmetric_score_matrices(member_count))
    chosen_thresholds = data.draw(thresholds)

    related_pairs = find_related_pairs(
        code_similarities, word_overlaps, chosen_thresholds
    )

    for first_index in range(member_count):
        for second_index in range(first_index + 1, member_count):
            is_similar_code = (
                code_similarities[first_index, second_index]
                >= chosen_thresholds.code_similarity
            )
            is_shared_vocabulary = (
                word_overlaps[first_index, second_index]
                >= chosen_thresholds.word_overlap
            )
            is_related = is_similar_code or is_shared_vocabulary

            assert ((first_index, second_index) in related_pairs) == is_related


@given(vocabulary_lists)
def test_word_overlap_matrix_property_holds_the_overlap_of_every_pair(
    vocabularies: list[frozenset[str]],
) -> None:
    matrix = word_overlap_matrix(vocabularies)

    assert matrix.shape == (len(vocabularies), len(vocabularies))

    for first_index, first_vocabulary in enumerate(vocabularies):
        for second_index, second_vocabulary in enumerate(vocabularies):
            expected_overlap = overlap_of(first_vocabulary, second_vocabulary)

            assert matrix[first_index, second_index] == expected_overlap
