from pathlib import Path

import numpy

from code_embeddings import (
    EmbeddingMatrix,
    embed_texts,
    embedded_text,
    embedding_key,
    load_code_model,
    no_embeddings,
)
from code_members import CodeMember, CodeUnit, members_of
from embedding_cache import read_embedding_cache, write_embedding_cache


def embed_member_sources(
    source_texts: list[str], models_directory: Path, cache_path: Path
) -> EmbeddingMatrix:
    texts = [embedded_text(source_text) for source_text in source_texts]
    keys = [embedding_key(text) for text in texts]
    cache = read_embedding_cache(cache_path)
    missing_texts_by_key: dict[str, str] = {}

    for key, text in zip(keys, texts, strict=True):
        if key not in cache:
            missing_texts_by_key[key] = text

    if missing_texts_by_key:
        code_model = load_code_model(models_directory)
        missing_texts = list(missing_texts_by_key.values())
        new_vectors = embed_texts(code_model, missing_texts)
        new_entries = dict(zip(missing_texts_by_key, new_vectors, strict=True))
        cache = {**cache, **new_entries}
        write_embedding_cache(cache_path, cache)

    if not keys:
        return no_embeddings()

    return numpy.array([cache[key] for key in keys], dtype=numpy.float32)


def embed_unit_members(
    units: tuple[CodeUnit, ...], models_directory: Path, cache_path: Path
) -> dict[CodeMember, EmbeddingMatrix]:
    members = members_of(units)
    source_texts = [member.source_text for member in members]
    vectors = embed_member_sources(source_texts, models_directory, cache_path)

    return dict(zip(members, vectors, strict=True))
