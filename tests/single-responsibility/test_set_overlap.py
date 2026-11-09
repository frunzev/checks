from hypothesis import given
from hypothesis import strategies as st

from set_overlap import overlap_of

word_sets = st.frozensets(st.text(min_size=1, max_size=6), max_size=6)
number_sets = st.frozensets(st.integers(min_value=0, max_value=20), max_size=8)


@given(word_sets, word_sets)
def test_overlap_of_property_is_symmetric_and_between_zero_and_one(
    first_words: frozenset[str], second_words: frozenset[str]
) -> None:
    overlap = overlap_of(first_words, second_words)

    assert overlap == overlap_of(second_words, first_words)
    assert 0.0 <= overlap <= 1.0


@given(number_sets.filter(bool))
def test_overlap_of_property_is_one_for_the_same_set(
    numbers: frozenset[int],
) -> None:
    assert overlap_of(numbers, numbers) == 1.0


@given(number_sets, number_sets)
def test_overlap_of_property_is_zero_without_a_shared_item(
    first_numbers: frozenset[int], second_numbers: frozenset[int]
) -> None:
    disjoint_numbers = second_numbers - first_numbers

    assert overlap_of(first_numbers, disjoint_numbers) == 0.0


@given(number_sets, number_sets)
def test_overlap_of_property_shrinks_when_an_unshared_item_is_added(
    first_numbers: frozenset[int], second_numbers: frozenset[int]
) -> None:
    unshared_number = max(first_numbers | second_numbers, default=0) + 1
    widened_numbers = first_numbers | {unshared_number}

    widened_overlap = overlap_of(widened_numbers, second_numbers)

    assert widened_overlap <= overlap_of(first_numbers, second_numbers)
