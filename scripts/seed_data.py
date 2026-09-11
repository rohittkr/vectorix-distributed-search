#!/usr/bin/env python3
"""
Generate a synthetic document dataset directly into PostgreSQL, in
streaming batches so memory stays flat regardless of --count.

Usage:
    python scripts/seed_data.py --count 10000
    python scripts/seed_data.py --count 1000000 --seed 42
    python scripts/seed_data.py --count 100000 --seed 42 --batch-size 1000

After seeding, documents are left with indexed_at = NULL; queue a
`/api/v1/index/reindex` job (or run the worker) to push them into
Elasticsearch.
"""
import argparse
import asyncio
import random
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from faker import Faker  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import create_all_tables, init_engine, session_scope  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.models.jobs import JobType  # noqa: E402
from app.services.indexing_service import IndexingService  # noqa: E402

CATEGORIES = [
    "technology", "science", "business", "health", "sports", "entertainment",
    "politics", "education", "travel", "food", "finance", "environment",
]
TAG_POOL = [
    "python", "distributed-systems", "machine-learning", "databases", "cloud",
    "security", "devops", "frontend", "backend", "networking", "ai", "startups",
    "research", "tutorial", "opinion", "news", "review", "case-study",
]
SOURCES = ["blog", "news-wire", "research-paper", "forum-post", "press-release", "internal-wiki"]


def _make_document(faker: Faker, idx: int) -> dict:
    title = faker.sentence(nb_words=random.randint(4, 9)).rstrip(".")
    paragraphs = faker.paragraphs(nb=random.randint(3, 8))
    content = "\n\n".join(paragraphs)
    description = faker.sentence(nb_words=random.randint(12, 20))
    category = random.choice(CATEGORIES)
    tags = random.sample(TAG_POOL, k=random.randint(1, 4))
    created_at = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 730))

    return {
        "id": str(uuid.uuid4()),
        "title": (title[:1].upper() + title[1:]) if title else f"Document {idx}",
        "content": content,
        "description": description,
        "category": category,
        "author": faker.name(),
        "tags": tags,
        "language": "en",
        "source": random.choice(SOURCES),
        "url": faker.url(),
        "popularity": round(random.paretovariate(1.5), 2),
        "doc_metadata": {"word_count": len(content.split())},
        "created_at": created_at,
        "updated_at": created_at,
        "indexed_at": None,
    }


async def seed(count: int, seed: int | None, batch_size: int) -> None:
    faker = Faker()
    if seed is not None:
        Faker.seed(seed)
        random.seed(seed)

    init_engine()
    await create_all_tables()

    start = time.perf_counter()
    inserted = 0

    async with session_scope() as session:
        while inserted < count:
            batch_count = min(batch_size, count - inserted)
            rows = [_make_document(faker, inserted + i) for i in range(batch_count)]

            # Raw bulk insert (not the ORM's add_all) -- meaningfully
            # faster at hundreds-of-thousands-of-rows scale.
            await session.execute(Document.__table__.insert(), rows)
            await session.commit()

            inserted += batch_count
            elapsed = time.perf_counter() - start
            rate = inserted / elapsed if elapsed > 0 else 0
            print(f"\rInserted {inserted:,}/{count:,} documents ({rate:,.0f} docs/sec)", end="", flush=True)

    elapsed = time.perf_counter() - start
    print(f"\nDone. Inserted {inserted:,} documents in {elapsed:.1f}s ({inserted / elapsed:,.0f} docs/sec).")

    async with session_scope() as session:
        service = IndexingService(session)
        job = await service.create_job(JobType.REINDEX)
        print(f"Queued indexing job {job.id} -- the worker container will pick it up automatically.")
        print("Watch progress with: python scripts/health_check.py  or  GET /api/v1/jobs/{job.id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=10_000, help="Number of documents to generate")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for deterministic generation")
    parser.add_argument("--batch-size", type=int, default=2000, help="Rows per DB insert batch")
    args = parser.parse_args()
    asyncio.run(seed(args.count, args.seed, args.batch_size))
