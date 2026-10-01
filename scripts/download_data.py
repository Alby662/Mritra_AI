"""Download the HI-Small files from Kaggle into data/raw and record SHA-256 checksums.

Needs a Kaggle API token in ~/.kaggle/kaggle.json (or KAGGLE_USERNAME / KAGGLE_KEY).
Downloads only the three files in configs/experiment.yaml, not the whole dataset.
"""

from __future__ import annotations

import hashlib
import logging
import zipfile
from pathlib import Path

from mritra.config import load_config, repo_path

logger = logging.getLogger("download_data")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    from kaggle.api.kaggle_api_extended import KaggleApi  # imported late: authenticates on import

    cfg = load_config()["dataset"]
    raw = repo_path(load_config()["paths"]["raw"])
    raw.mkdir(parents=True, exist_ok=True)

    api = KaggleApi()
    api.authenticate()
    for name in cfg["files"].values():
        target = raw / name
        if target.exists():
            logger.info("present: %s", name)
            continue
        logger.info("downloading: %s", name)
        api.dataset_download_file(cfg["kaggle_slug"], name, path=str(raw), quiet=False)
        zipped = raw / f"{name}.zip"
        if zipped.exists():
            with zipfile.ZipFile(zipped) as z:
                z.extractall(raw)
            zipped.unlink()
        if not target.exists():
            raise FileNotFoundError(f"download did not produce {target}")

    lines = [f"{sha256_file(raw / n)}  {n}" for n in sorted(cfg["files"].values())]
    (raw / "CHECKSUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("checksums written to %s", raw / "CHECKSUMS")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    main()
