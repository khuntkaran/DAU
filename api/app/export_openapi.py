"""Writes the OpenAPI schema so the web app can generate types without running the API.

Usage: node scripts/py.mjs api.app.export_openapi [path]
"""

import json
import sys
from pathlib import Path

from api.app.main import app

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> None:
    path = Path(argv[1]) if len(argv) > 1 else DEFAULT_PATH
    path.write_text(render(), encoding="utf-8", newline="\n")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main(sys.argv)
