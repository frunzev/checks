import numpy
from numpy.typing import NDArray

class InferenceSession:
    def __init__(self, path_or_bytes: str) -> None: ...
    def run(
        self,
        output_names: list[str] | None,
        input_feed: dict[str, NDArray[numpy.int64]],
    ) -> list[NDArray[numpy.float32]]: ...
