from dataclasses import dataclass

from branch_tokens import head_tokens, head_values
from code_members import BranchHead, CodeMember
from variant_families import MINIMUM_FAMILY_SIZE, find_variant_families

SWITCH_CASE_KEYWORD = "case"
MINIMUM_PLACES = 2
PLACE_SEPARATOR = ", "


@dataclass(frozen=True)
class RepeatedDispatch:
    variants: frozenset[str]
    places: tuple[CodeMember, ...]


def is_dispatch_on(
    variants: frozenset[str], branch_heads: tuple[BranchHead, ...]
) -> bool:
    for first_position, first_head in enumerate(branch_heads):
        for second_head in branch_heads[first_position + 1 :]:
            if _branch_on_one_subject(variants, first_head, second_head):
                return True

    return False


def find_repeated_dispatches(
    members: tuple[CodeMember, ...],
) -> tuple[RepeatedDispatch, ...]:
    token_sets = [_member_head_tokens(member) for member in members]
    dispatches: list[RepeatedDispatch] = []

    for variants in find_variant_families(token_sets):
        places: list[CodeMember] = []

        for member, member_tokens in zip(members, token_sets, strict=True):
            family_mentions = len(member_tokens & variants)

            if family_mentions < MINIMUM_FAMILY_SIZE:
                continue

            if is_dispatch_on(variants, member.branch_heads):
                places.append(member)

        if len(places) >= MINIMUM_PLACES:
            dispatches.append(RepeatedDispatch(variants, tuple(places)))

    return tuple(dispatches)


def describe_dispatch_place(
    place: CodeMember, dispatch: RepeatedDispatch
) -> str:
    other_places: list[str] = []

    for other_place in dispatch.places:
        if other_place != place:
            location = f"{other_place.path}:{other_place.line}"
            other_places.append(f"{location} {other_place.display_name}")

    listed_variants = PLACE_SEPARATOR.join(sorted(dispatch.variants))

    return (
        f"{place.path}:{place.line}: {place.display_name} branches on"
        f" {listed_variants}, as do {PLACE_SEPARATOR.join(other_places)}"
    )


def _branch_on_one_subject(
    variants: frozenset[str], first_head: BranchHead, second_head: BranchHead
) -> bool:
    first_tokens = head_tokens(first_head.condition)
    second_tokens = head_tokens(second_head.condition)
    first_values = head_values(first_head.condition) & variants
    second_values = head_values(second_head.condition) & variants
    only_first_values = first_values - second_tokens
    only_second_values = second_values - first_tokens
    shares_subject = bool(first_tokens & second_tokens)
    are_switch_cases = (
        first_head.keyword == SWITCH_CASE_KEYWORD
        and second_head.keyword == SWITCH_CASE_KEYWORD
    )

    if not only_first_values or not only_second_values:
        return False

    return shares_subject or are_switch_cases


def _member_head_tokens(member: CodeMember) -> frozenset[str]:
    tokens: set[str] = set()

    for branch_head in member.branch_heads:
        tokens.update(head_tokens(branch_head.condition))

    return frozenset(tokens)
