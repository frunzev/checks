from pathlib import Path
from typing import TYPE_CHECKING, cast

import numpy
from numpy.typing import NDArray

if TYPE_CHECKING:
    from numpy.lib.npyio import NpzFile

type EmbeddingCache = dict[str, NDArray[numpy.float32]]

KEYS_ARRAY = "keys"
VECTORS_ARRAY = "vectors"
PARTIAL_SUFFIX = ".partial"


def read_embedding_cache(cache_path: Path) -> EmbeddingCache:
    if not cache_path.exists():
        return {}

    stored_arrays = cast("NpzFile", numpy.load(cache_path))

    with stored_arrays:
        keys = cast("list[str]", stored_arrays[KEYS_ARRAY].tolist())
        vectors = cast(
            "list[NDArray[numpy.float32]]",
            list(stored_arrays[VECTORS_ARRAY]),
        )

    cache: EmbeddingCache = {}

    for key, vector in zip(keys, vectors, strict=True):
        cache[key] = vector

    return cache


def write_embedding_cache(cache_path: Path, cache: EmbeddingCache) -> None:
    keys = numpy.array(list(cache), dtype=str)
    vectors = numpy.array(list(cache.values()), dtype=numpy.float32)
    partial_path = cache_path.with_name(cache_path.name + PARTIAL_SUFFIX)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    with partial_path.open("wb") as partial_file:
        numpy.savez(partial_file, keys=keys, vectors=vectors)

    _ = partial_path.replace(cache_path)
