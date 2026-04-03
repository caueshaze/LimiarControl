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
    import_base_item_seed_file,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import base item catalog from JSON seed into the database.",
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_BASE_ITEMS_SEED_PATH),
        help="Path to the JSON seed file.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Deactivate existing base items missing from the file for the systems present before importing.",
    )
    args = parser.parse_args()

    with Session(engine) as session:
        result = import_base_item_seed_file(
            session,
            path=Path(args.input),
            replace=args.replace,
        )

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
