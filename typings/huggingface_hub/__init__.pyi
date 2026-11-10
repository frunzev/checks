from pathlib import Path

def hf_hub_download(
    repo_id: str,
    filename: str,
    *,
    revision: str,
    cache_dir: Path,
    local_files_only: bool = ...,
) -> str: ...
