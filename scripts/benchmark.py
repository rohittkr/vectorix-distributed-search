#!/usr/bin/env python3
"""
Performance benchmark against a *running* instance of the backend
(local dev server or the Docker Compose stack).

Measures real p50/p95/p99 search latency, throughput, error rate, and
cache hit rate -- never fabricates numbers. If the backend is
unreachable, it reports a connection error rather than pretending.

Usage:
    python scripts/benchmark.py --base-url http://localhost:8000 --requests 200 --concurrency 20
"""
import argparse
import asyncio
import statistics
import time

import httpx

SAMPLE_QUERIES = [
    "distributed systems", "machine learning", "database performance",
    "cloud infrastructure", "security best practices", "python tutorial",
    "microservices architecture", "data pipeline", "kubernetes deployment",
    "api design",
]


async def _one_search(client: httpx.AsyncClient, base_url: str, query: str) -> tuple[float, bool, bool]:
    start = time.perf_counter()
    try:
        resp = await client.post(f"{base_url}/api/v1/search", json={"query": query}, timeout=10.0)
        elapsed_ms = (time.perf_counter() - start) * 1000
        ok = resp.status_code == 200
        cache_hit = resp.json().get("cache_hit", False) if ok else False
        return elapsed_ms, ok, cache_hit
    except httpx.HTTPError:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return elapsed_ms, False, False


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = min(int(len(values) * pct), len(values) - 1)
    return values[idx]


async def run_benchmark(base_url: str, total_requests: int, concurrency: int) -> None:
    async with httpx.AsyncClient() as client:
        try:
            health = await client.get(f"{base_url}/api/v1/health/ready", timeout=5.0)
            print(f"Backend readiness: {health.json()}")
        except httpx.HTTPError as exc:
            print(f"ERROR: could not reach backend at {base_url}: {exc}")
            print("Start the stack first: docker compose up --build")
            return

        semaphore = asyncio.Semaphore(concurrency)
        latencies: list[float] = []
        errors = 0
        cache_hits = 0

        async def bound_search(i: int):
            nonlocal errors, cache_hits
            async with semaphore:
                query = SAMPLE_QUERIES[i % len(SAMPLE_QUERIES)]
                latency, ok, cache_hit = await _one_search(client, base_url, query)
                latencies.append(latency)
                if not ok:
                    errors += 1
                if cache_hit:
                    cache_hits += 1

        start = time.perf_counter()
        await asyncio.gather(*[bound_search(i) for i in range(total_requests)])
        wall_time = time.perf_counter() - start

        print("\n--- Benchmark Report ---")
        print(f"Total requests:     {total_requests}")
        print(f"Concurrency:        {concurrency}")
        print(f"Wall time:          {wall_time:.2f}s")
        print(f"Throughput:         {total_requests / wall_time:.1f} req/s")
        print(f"Error rate:         {errors / total_requests:.2%}")
        print(f"Cache hit rate:     {cache_hits / total_requests:.2%}")
        print(f"p50 latency:        {_percentile(latencies, 0.50):.1f} ms")
        print(f"p95 latency:        {_percentile(latencies, 0.95):.1f} ms")
        print(f"p99 latency:        {_percentile(latencies, 0.99):.1f} ms")
        print(f"mean latency:       {statistics.mean(latencies):.1f} ms" if latencies else "mean latency: n/a")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.base_url, args.requests, args.concurrency))
