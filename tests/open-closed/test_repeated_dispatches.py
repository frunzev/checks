from hypothesis import given
from hypothesis import strategies as st

from code_members import BranchHead, CodeMember
from repeated_dispatches import (
    RepeatedDispatch,
    describe_dispatch_place,
    find_repeated_dispatches,
    is_dispatch_on,
)
from semantic_finder_support import code_member

variant_words = st.from_regex(r"[a-m]{3,6}", fullmatch=True)
subject_words = st.from_regex(r"[n-z]{3,6}", fullmatch=True)
variant_sets = st.lists(variant_words, min_size=3, max_size=5, unique=True)
place_counts = st.integers(min_value=2, max_value=4)
keywords = st.sampled_from(["if", "elif", "case"])


def _if_chain(subject: str, values: list[str]) -> tuple[BranchHead, ...]:
    heads: list[BranchHead] = []

    for value in values:
        condition = f' {subject} == "{value}"'
        heads.append(BranchHead(keyword="if", condition=condition))

    return tuple(heads)


def _case_list(values: list[str]) -> tuple[BranchHead, ...]:
    heads: list[BranchHead] = []

    for value in values:
        heads.append(BranchHead(keyword="case", condition=f' "{value}"'))

    return tuple(heads)


def _dispatching_places(
    subject: str, values: list[str], place_count: int
) -> list[CodeMember]:
    places: list[CodeMember] = []

    for position in range(place_count):
        if position % 2 == 0:
            heads = _if_chain(subject, values)
        else:
            heads = _case_list(values)

        place = code_member(f"handle_{position}", (), None, position + 1, heads)
        places.append(place)

    return places


@given(subject_words, variant_sets)
def test_is_dispatch_on_property_accepts_one_subject_with_many_values(
    subject: str, values: list[str]
) -> None:
    assert is_dispatch_on(frozenset(values), _if_chain(subject, values))


@given(variant_sets)
def test_is_dispatch_on_property_accepts_switch_cases(
    values: list[str],
) -> None:
    assert is_dispatch_on(frozenset(values), _case_list(values))


@given(subject_words, variant_sets, keywords)
def test_is_dispatch_on_property_rejects_a_single_branch(
    subject: str, values: list[str], keyword: str
) -> None:
    condition = " and ".join(f"{subject} == {value}" for value in values)
    single_head = (BranchHead(keyword=keyword, condition=condition),)

    assert not is_dispatch_on(frozenset(values), single_head)


@given(variant_sets)
def test_is_dispatch_on_property_rejects_if_branches_on_other_subjects(
    values: list[str],
) -> None:
    heads = tuple(
        BranchHead(keyword="if", condition=f" {value}") for value in values
    )

    assert not is_dispatch_on(frozenset(values), heads)


@given(subject_words, variant_sets, place_counts)
def test_find_repeated_dispatches_property_finds_every_dispatching_place(
    subject: str, values: list[str], place_count: int
) -> None:
    places = _dispatching_places(subject, values, place_count)

    dispatches = find_repeated_dispatches(tuple(places))

    assert len(dispatches) == 1
    assert frozenset(values) <= dispatches[0].variants
    assert dispatches[0].places == tuple(places)


@given(subject_words, variant_sets)
def test_find_repeated_dispatches_property_ignores_a_single_place(
    subject: str, values: list[str]
) -> None:
    places = _dispatching_places(subject, values, 1)

    assert find_repeated_dispatches(tuple(places)) == ()


@given(subject_words, variant_sets, place_counts)
def test_describe_dispatch_place_property_names_the_place_and_the_others(
    subject: str, values: list[str], place_count: int
) -> None:
    places = _dispatching_places(subject, values, place_count)
    dispatch = RepeatedDispatch(
        variants=frozenset(values), places=tuple(places)
    )

    description = describe_dispatch_place(places[0], dispatch)
    listed_variants = ", ".join(sorted(values))

    assert description.startswith(
        f"{places[0].path}:{places[0].line}: {places[0].display_name}"
        f" branches on {listed_variants}, as do "
    )

    for other_place in places[1:]:
        assert f"{other_place.path}:{other_place.line}" in description

    assert f"{places[0].path}:{places[0].line} " not in description


@given(subject_words, variant_sets)
def test_is_dispatch_on_property_rejects_branches_on_plain_variables(
    subject: str, values: list[str]
) -> None:
    heads = tuple(
        BranchHead(keyword="if", condition=f" {subject} > {value}")
        for value in values
    )

    assert not is_dispatch_on(frozenset(values), heads)
