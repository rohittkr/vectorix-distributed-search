#!/usr/bin/env python3
"""
Create (or recreate) the `documents` Elasticsearch index with the
mapping/settings defined in app.search.mappings.

Usage:
    python scripts/create_index.py
    python scripts/create_index.py --recreate   # drop and recreate
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.search.es_client import build_client  # noqa: E402
from app.search.mappings import build_index_body  # noqa: E402


async def main(recreate: bool) -> None:
    settings = get_settings()
    client = build_client()
    index_name = settings.ELASTICSEARCH_INDEX

    exists = await client.indices.exists(index=index_name)
    if exists:
        if not recreate:
            print(f"Index '{index_name}' already exists. Use --recreate to drop and rebuild it.")
            await client.close()
            return
        print(f"Deleting existing index '{index_name}'...")
        await client.indices.delete(index=index_name)

    print(f"Creating index '{index_name}'...")
    await client.indices.create(index=index_name, body=build_index_body())
    print("Done.")
    await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--recreate", action="store_true", help="Drop and recreate the index if it exists")
    args = parser.parse_args()
    asyncio.run(main(args.recreate))
