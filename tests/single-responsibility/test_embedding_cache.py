import tempfile
from pathlib import Path

import numpy
from hypothesis import given
from hypothesis import strategies as st

from embedding_cache import (
    EmbeddingCache,
    read_embedding_cache,
    write_embedding_cache,
)

VECTOR_SIZE = 4
cache_keys = st.from_regex(r"[0-9a-f]{64}", fullmatch=True)
vector_values = st.lists(
    st.floats(min_value=-1.0, max_value=1.0, width=32),
    min_size=VECTOR_SIZE,
    max_size=VECTOR_SIZE,
)
cache_contents = st.dictionaries(cache_keys, vector_values, max_size=5)


def _cache_from(contents: dict[str, list[float]]) -> EmbeddingCache:
    cache: EmbeddingCache = {}

    for key, values in contents.items():
        cache[key] = numpy.array(values, dtype=numpy.float32)

    return cache


@given(st.from_regex(r"[a-z]{1,10}\.npz", fullmatch=True))
def test_read_embedding_cache_property_is_empty_without_a_cache_file(
    file_name: str,
) -> None:
    with tempfile.TemporaryDirectory() as directory_name:
        cache = read_embedding_cache(Path(directory_name) / file_name)

    assert cache == {}


@given(cache_contents)
def test_write_embedding_cache_property_round_trips_every_vector(
    contents: dict[str, list[float]],
) -> None:
    written_cache = _cache_from(contents)

    with tempfile.TemporaryDirectory() as directory_name:
        cache_path = Path(directory_name) / "nested" / "embeddings.npz"
        write_embedding_cache(cache_path, written_cache)
        read_cache = read_embedding_cache(cache_path)

    assert sorted(read_cache) == sorted(written_cache)

    for key, vector in written_cache.items():
        assert numpy.array_equal(read_cache[key], vector)


@given(cache_contents)
def test_write_embedding_cache_property_leaves_only_the_cache_file(
    contents: dict[str, list[float]],
) -> None:
    with tempfile.TemporaryDirectory() as directory_name:
        cache_path = Path(directory_name) / "embeddings.npz"
        write_embedding_cache(cache_path, _cache_from(contents))
        left_files = sorted(Path(directory_name).iterdir())

    assert left_files == [cache_path]
