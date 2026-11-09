def overlap_of[Item](first: frozenset[Item], second: frozenset[Item]) -> float:
    all_items = first | second

    if not all_items:
        return 0.0

    shared_items = first & second

    return len(shared_items) / len(all_items)
