"""Download whisper.cpp GGML model files."""

from __future__ import annotations

import sys
from pathlib import Path

BASE_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
MODELS_DIR = Path(__file__).parent.parent / "models"

MODELS = {
    "tiny": "ggml-tiny.bin",
    "base": "ggml-base.bin",
    "small": "ggml-small.bin",
}


def download(model_name: str = "base") -> Path:
    filename = MODELS.get(model_name)
    if not filename:
        print(f"Unknown model: {model_name}. Choose from: {list(MODELS.keys())}")
        sys.exit(1)

    dest = MODELS_DIR / filename
    if dest.exists():
        print(f"Model already exists: {dest}")
        return dest

    url = f"{BASE_URL}/{filename}"
    print(f"Downloading {model_name} model from {url} ...")

    import requests
    from tqdm import tqdm

    resp = requests.get(url, stream=True, timeout=300)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f, tqdm(total=total, unit="B", unit_scale=True) as bar:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            bar.update(len(chunk))

    print(f"Saved to {dest}")
    return dest


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "base"
    download(name)
