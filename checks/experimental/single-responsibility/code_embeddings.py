import hashlib
from pathlib import Path

import numpy
from fastembed import TextEmbedding
from numpy.typing import NDArray

type EmbeddingMatrix = NDArray[numpy.float32]

CODE_MODEL_NAME = "jinaai/jina-embeddings-v2-base-code"
CODE_VECTOR_SIZE = 768
MAXIMUM_EMBEDDED_CHARACTERS = 600
EMBEDDING_BATCH_SIZE = 16
KEY_ENCODING = "utf-8"


def embedded_text(source_text: str) -> str:
    return source_text[:MAXIMUM_EMBEDDED_CHARACTERS]


def embedding_key(text: str) -> str:
    keyed_text = f"{CODE_MODEL_NAME}\n{text}"

    return hashlib.sha256(keyed_text.encode(KEY_ENCODING)).hexdigest()


def normalize_rows(vectors: EmbeddingMatrix) -> EmbeddingMatrix:
    row_lengths = numpy.linalg.norm(vectors, axis=1, keepdims=True)

    return vectors / row_lengths


def no_embeddings() -> EmbeddingMatrix:
    return numpy.empty((0, CODE_VECTOR_SIZE), dtype=numpy.float32)


def download_code_model(models_directory: Path) -> None:
    _ = TextEmbedding(
        CODE_MODEL_NAME, cache_dir=str(models_directory), lazy_load=True
    )


def load_code_model(models_directory: Path) -> TextEmbedding:
    try:
        return TextEmbedding(
            CODE_MODEL_NAME,
            cache_dir=str(models_directory),
            local_files_only=True,
        )
    except ValueError as error:
        message = (
            f"the code model is not in {models_directory} -"
            " run ./install.sh in the toolkit"
        )
        raise ValueError(message) from error


def embed_texts(code_model: TextEmbedding, texts: list[str]) -> EmbeddingMatrix:
    if not texts:
        return no_embeddings()

    vectors = list(code_model.embed(texts, batch_size=EMBEDDING_BATCH_SIZE))
    matrix = numpy.array(vectors, dtype=numpy.float32)

    return normalize_rows(matrix)
