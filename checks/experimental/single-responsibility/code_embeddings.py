import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy
import onnxruntime
from huggingface_hub import hf_hub_download
from huggingface_hub.errors import LocalEntryNotFoundError
from numpy.typing import NDArray
from tokenizers import Tokenizer

type EmbeddingMatrix = NDArray[numpy.float32]
type AttentionMask = NDArray[numpy.int64]

CODE_MODEL_NAME = "jinaai/jina-embeddings-v2-base-code"
CODE_MODEL_REVISION = "516f4baf13dec4ddddda8631e019b5737c8bc250"
MODEL_FILE = "onnx/model.onnx"
TOKENIZER_FILE = "tokenizer.json"
CODE_MODEL_FILES = (MODEL_FILE, TOKENIZER_FILE)
PADDING_TOKEN = "<pad>"
CODE_VECTOR_SIZE = 768
MAXIMUM_EMBEDDED_CHARACTERS = 600
EMBEDDING_BATCH_SIZE = 16
KEY_ENCODING = "utf-8"
SMALLEST_TOKEN_COUNT = 1e-9
PADDED_ATTENTION = 0


@dataclass(frozen=True)
class CodeModel:
    session: onnxruntime.InferenceSession
    tokenizer: Tokenizer
    padding_id: int


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


def mean_pooled(
    hidden_states: EmbeddingMatrix, attention_mask: AttentionMask
) -> EmbeddingMatrix:
    token_weights = attention_mask[:, :, numpy.newaxis].astype(numpy.float32)
    summed_states = (hidden_states * token_weights).sum(axis=1)
    token_counts = numpy.maximum(
        token_weights.sum(axis=1), SMALLEST_TOKEN_COUNT
    )
    pooled_states = summed_states / token_counts

    return pooled_states.astype(numpy.float32)


def download_code_model(models_directory: Path) -> None:
    for file_name in CODE_MODEL_FILES:
        _ = hf_hub_download(
            CODE_MODEL_NAME,
            file_name,
            revision=CODE_MODEL_REVISION,
            cache_dir=models_directory,
        )


def load_code_model(models_directory: Path) -> CodeModel:
    try:
        model_path = _installed_model_file(models_directory, MODEL_FILE)
        tokenizer_path = _installed_model_file(
            models_directory, TOKENIZER_FILE
        )
    except LocalEntryNotFoundError as error:
        message = (
            f"the code model is not in {models_directory} -"
            " run ./install.sh in the toolkit"
        )
        raise ValueError(message) from error

    session = onnxruntime.InferenceSession(model_path)
    tokenizer = Tokenizer.from_file(tokenizer_path)
    padding_id = tokenizer.token_to_id(PADDING_TOKEN)

    if padding_id is None:
        message = f"the code model tokenizer has no {PADDING_TOKEN} token"
        raise ValueError(message)

    return CodeModel(
        session=session, tokenizer=tokenizer, padding_id=padding_id
    )


def embed_texts(code_model: CodeModel, texts: list[str]) -> EmbeddingMatrix:
    if not texts:
        return no_embeddings()

    batches: list[EmbeddingMatrix] = []

    for batch_start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch_texts = texts[batch_start : batch_start + EMBEDDING_BATCH_SIZE]
        batches.append(_embed_batch(code_model, batch_texts))

    return numpy.concatenate(batches)


def _embed_batch(code_model: CodeModel, texts: list[str]) -> EmbeddingMatrix:
    encodings = code_model.tokenizer.encode_batch(texts)
    id_rows = [encoding.ids for encoding in encodings]
    mask_rows = [encoding.attention_mask for encoding in encodings]
    token_ids = padded_rows(id_rows, code_model.padding_id)
    attention_mask = padded_rows(mask_rows, PADDED_ATTENTION)
    model_inputs = {"input_ids": token_ids, "attention_mask": attention_mask}
    hidden_states = code_model.session.run(None, model_inputs)[0]

    return normalize_rows(mean_pooled(hidden_states, attention_mask))


def padded_rows(rows: list[list[int]], filler: int) -> AttentionMask:
    longest_row = max(len(row) for row in rows)
    padded: list[list[int]] = []

    for row in rows:
        padded.append(row + [filler] * (longest_row - len(row)))

    return numpy.array(padded, dtype=numpy.int64)


def _installed_model_file(models_directory: Path, file_name: str) -> str:
    return hf_hub_download(
        CODE_MODEL_NAME,
        file_name,
        revision=CODE_MODEL_REVISION,
        cache_dir=models_directory,
        local_files_only=True,
    )
