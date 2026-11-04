"""Download third-party evaluation data into ``data/raw/``.

Maternal Health Risk dataset, UCI Machine Learning Repository, id 863
(also mirrored on Kaggle). Licence: CC BY 4.0. Citation: Ahmed, M. and
Kashem, M. A. (2020), "Maternal Health Risk", UCI Machine Learning
Repository, https://doi.org/10.24432/C5DP5D.

The file is fetched rather than committed so the repository does not
redistribute third-party data.
"""

from __future__ import annotations

import io
import urllib.request
import zipfile
from pathlib import Path

URL = ("https://archive.ics.uci.edu/static/public/863/"
       "maternal+health+risk.zip")
TARGET = Path(__file__).resolve().parents[1] / "data" / "external"


def main() -> None:
    """Download and unzip the dataset."""
    TARGET.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(URL, timeout=30) as response:  # noqa: S310
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    archive.extractall(TARGET)
    print("Saved:", ", ".join(archive.namelist()), "->", TARGET)


if __name__ == "__main__":
    main()
