#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPO_ROOT / "server_py"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from sqlmodel import Session

from app.db.session import engine
from app.services.base_item_seeds import (
    DEFAULT_BASE_ITEMS_SEED_PATH,
    export_base_item_seed_document,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export the current base item catalog to a JSON seed file.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_BASE_ITEMS_SEED_PATH),
        help="Destination path for the JSON seed file.",
    )
    args = parser.parse_args()

    with Session(engine) as session:
        document = export_base_item_seed_document(
            session,
            path=Path(args.output),
        )

    print({"version": document.version, "items": len(document.items), "output": args.output})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
