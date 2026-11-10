import functools
import tempfile
from pathlib import Path

import numpy
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from numpy.typing import NDArray

from code_embeddings import (
    CODE_VECTOR_SIZE,
    MAXIMUM_EMBEDDED_CHARACTERS,
    CodeModel,
    EmbeddingMatrix,
    embed_texts,
    embedded_text,
    embedding_key,
    load_code_model,
    mean_pooled,
    no_embeddings,
    normalize_rows,
    padded_rows,
)
from embedding_cache import (
    EmbeddingCache,
    read_embedding_cache,
    write_embedding_cache,
)
from member_embeddings import embed_member_sources, embed_unit_members
from semantic_finder_support import (
    CODE_MODELS_DIRECTORY,
    code_member,
    code_unit,
    lowercase_words,
    unique_member_names,
)

MODEL_SETTINGS = settings(max_examples=3, deadline=None)
FILE_SETTINGS = settings(deadline=None)
VECTOR_SIZE = 3
UNIT_LENGTH_TOLERANCE = 1e-5
source_texts = st.lists(st.text(min_size=1, max_size=40), max_size=4)
nonzero_rows = st.lists(
    st.lists(
        st.floats(min_value=0.5, max_value=10.0, width=32),
        min_size=VECTOR_SIZE,
        max_size=VECTOR_SIZE,
    ),
    min_size=1,
    max_size=4,
)
hidden_values = st.floats(min_value=-10.0, max_value=10.0, width=32)
sequence_lengths = st.integers(min_value=1, max_value=5)


@functools.cache
def _code_model() -> CodeModel:
    return load_code_model(CODE_MODELS_DIRECTORY)


def _row_lengths(vectors: EmbeddingMatrix) -> list[float]:
    lengths: list[float] = []

    for row in vectors:
        lengths.append(float(numpy.linalg.norm(row)))

    return lengths


@given(st.text(max_size=MAXIMUM_EMBEDDED_CHARACTERS * 2))
def test_embedded_text_property_is_a_bounded_prefix_of_the_source(
    source_text: str,
) -> None:
    text = embedded_text(source_text)

    assert source_text.startswith(text)
    assert len(text) == min(len(source_text), MAXIMUM_EMBEDDED_CHARACTERS)


@given(st.text(), st.text())
def test_embedding_key_property_differs_exactly_when_the_text_differs(
    first_text: str, second_text: str
) -> None:
    keys_are_equal = embedding_key(first_text) == embedding_key(second_text)

    assert keys_are_equal == (first_text == second_text)


@given(nonzero_rows)
def test_normalize_rows_property_gives_every_row_unit_length(
    rows: list[list[float]],
) -> None:
    vectors = numpy.array(rows, dtype=numpy.float32)

    for length in _row_lengths(normalize_rows(vectors)):
        assert abs(length - 1.0) < UNIT_LENGTH_TOLERANCE


@given(nonzero_rows)
def test_normalize_rows_property_keeps_the_direction_of_every_row(
    rows: list[list[float]],
) -> None:
    vectors = numpy.array(rows, dtype=numpy.float32)

    normalized_vectors = normalize_rows(vectors)

    for row, normalized_row in zip(vectors, normalized_vectors, strict=True):
        cosine = float(row @ normalized_row) / float(numpy.linalg.norm(row))

        assert abs(cosine - 1.0) < UNIT_LENGTH_TOLERANCE


@given(lowercase_words)
def test_load_code_model_property_rejects_a_folder_without_the_model(
    folder_name: str,
) -> None:
    with tempfile.TemporaryDirectory() as directory_name:
        models_directory = Path(directory_name) / folder_name

        with pytest.raises(ValueError, match=r"install\.sh"):
            _ = load_code_model(models_directory)


@MODEL_SETTINGS
@given(source_texts)
def test_embed_texts_property_returns_one_unit_vector_per_text(
    texts: list[str],
) -> None:
    vectors = embed_texts(_code_model(), texts)

    assert len(vectors) == len(texts)

    for length in _row_lengths(vectors):
        assert abs(length - 1.0) < UNIT_LENGTH_TOLERANCE


@FILE_SETTINGS
@given(source_texts)
def test_embed_member_sources_property_reuses_cached_vectors_in_order(
    texts: list[str],
) -> None:
    cached_vectors: EmbeddingCache = {}

    for position, text in enumerate(texts):
        vector = numpy.full(VECTOR_SIZE, position, dtype=numpy.float32)
        cached_vectors[embedding_key(embedded_text(text))] = vector

    with tempfile.TemporaryDirectory() as directory_name:
        cache_path = Path(directory_name) / "embeddings.npz"
        missing_models = Path(directory_name) / "no-models"
        write_embedding_cache(cache_path, cached_vectors)

        vectors = embed_member_sources(texts, missing_models, cache_path)

    for text, vector in zip(texts, vectors, strict=True):
        expected = cached_vectors[embedding_key(embedded_text(text))]

        assert numpy.array_equal(vector, expected)


@MODEL_SETTINGS
@given(source_texts)
def test_embed_member_sources_property_caches_every_new_text(
    texts: list[str],
) -> None:
    with tempfile.TemporaryDirectory() as directory_name:
        cache_path = Path(directory_name) / "embeddings.npz"

        _ = embed_member_sources(texts, CODE_MODELS_DIRECTORY, cache_path)
        cache = read_embedding_cache(cache_path)

    for text in texts:
        assert embedding_key(embedded_text(text)) in cache


def test_no_embeddings_has_no_rows_of_the_code_vector_size() -> None:
    assert no_embeddings().shape == (0, CODE_VECTOR_SIZE)


@FILE_SETTINGS
@given(unique_member_names)
def test_embed_unit_members_property_maps_every_member_to_its_vector(
    names: list[str],
) -> None:
    members = [code_member(name, (), None, 1) for name in names]
    cached_vectors: EmbeddingCache = {}

    for position, member in enumerate(members):
        vector = numpy.full(VECTOR_SIZE, position, dtype=numpy.float32)
        member_key = embedding_key(embedded_text(member.source_text))
        cached_vectors[member_key] = vector

    with tempfile.TemporaryDirectory() as directory_name:
        cache_path = Path(directory_name) / "embeddings.npz"
        missing_models = Path(directory_name) / "no-models"
        write_embedding_cache(cache_path, cached_vectors)
        units = (code_unit(tuple(members)),)

        vectors_by_member = embed_unit_members(
            units, missing_models, cache_path
        )

    assert list(vectors_by_member) == members

    for member, vector in vectors_by_member.items():
        member_key = embedding_key(embedded_text(member.source_text))
        expected = cached_vectors[member_key]

        assert numpy.array_equal(vector, expected)


@st.composite
def hidden_state_batches(
    draw: st.DrawFn,
) -> tuple[EmbeddingMatrix, NDArray[numpy.int64]]:
    sequence_length = draw(sequence_lengths)
    values = draw(
        st.lists(
            hidden_values,
            min_size=sequence_length * VECTOR_SIZE,
            max_size=sequence_length * VECTOR_SIZE,
        )
    )
    hidden_states = numpy.array(values, dtype=numpy.float32).reshape(
        1, sequence_length, VECTOR_SIZE
    )
    real_tokens = draw(st.integers(min_value=1, max_value=sequence_length))
    mask_values = [1] * real_tokens + [0] * (sequence_length - real_tokens)
    attention_mask = numpy.array([mask_values], dtype=numpy.int64)

    return hidden_states, attention_mask


@given(hidden_state_batches())
def test_mean_pooled_property_averages_only_the_real_tokens(
    batch: tuple[EmbeddingMatrix, NDArray[numpy.int64]],
) -> None:
    hidden_states, attention_mask = batch
    real_tokens = int(attention_mask.sum())
    expected = hidden_states[0, :real_tokens].mean(axis=0)

    pooled = mean_pooled(hidden_states, attention_mask)

    assert numpy.allclose(pooled[0], expected, atol=1e-5)


@given(hidden_state_batches(), hidden_values)
def test_mean_pooled_property_ignores_what_padding_holds(
    batch: tuple[EmbeddingMatrix, NDArray[numpy.int64]],
    padding_value: float,
) -> None:
    hidden_states, attention_mask = batch
    changed_states = hidden_states.copy()
    changed_states[attention_mask == 0] = padding_value

    pooled = mean_pooled(hidden_states, attention_mask)
    changed_pooled = mean_pooled(changed_states, attention_mask)

    assert numpy.allclose(pooled, changed_pooled, atol=1e-6)


@given(
    st.lists(
        st.lists(st.integers(min_value=0, max_value=50), max_size=6),
        min_size=1,
        max_size=4,
    ),
    st.integers(min_value=0, max_value=3),
)
def test_padded_rows_property_fills_every_row_to_the_longest(
    rows: list[list[int]], filler: int
) -> None:
    padded = padded_rows(rows, filler)
    longest_row = max(len(row) for row in rows)

    assert padded.shape == (len(rows), longest_row)

    for row, padded_row in zip(rows, padded.tolist(), strict=True):
        assert padded_row[: len(row)] == row
        assert padded_row[len(row) :] == [filler] * (longest_row - len(row))
