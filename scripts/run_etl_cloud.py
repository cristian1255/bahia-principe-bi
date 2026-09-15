"""Download the configured source file and load it into the shared database."""

import json
import os
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from etl_pipeline import ejecutar_etl_desde_archivo


def main() -> None:
    source_url = os.environ.get("ETL_SOURCE_URL")
    if not source_url:
        raise RuntimeError("ETL_SOURCE_URL is required; no source data was configured")

    headers = {}
    token = os.environ.get("ETL_SOURCE_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(source_url, headers=headers)
    with urlopen(request, timeout=120) as response:
        payload = response.read()

    configured_format = os.environ.get("ETL_SOURCE_FORMAT", "").lower().strip()
    suffix = ".csv" if configured_format == "csv" else ".xlsx"
    source_suffix = Path(urlparse(source_url).path).suffix.lower()
    if source_suffix in {".csv", ".xlsx"}:
        suffix = source_suffix

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary_file:
        temporary_file.write(payload)
        temporary_path = temporary_file.name

    try:
        summary = ejecutar_etl_desde_archivo(temporary_path, es_csv=suffix == ".csv")
        print(json.dumps(summary, default=str, ensure_ascii=False))
    finally:
        Path(temporary_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
