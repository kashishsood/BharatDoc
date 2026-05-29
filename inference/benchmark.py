"""
BharatDoc-VLM: Inference Benchmark
=====================================

Runs 100 sequential + 100 concurrent requests against the inference server.
Reports p50, p95, p99 latency and requests/sec throughput.
"""

from __future__ import annotations

import asyncio
import io
import logging
import time

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def create_test_image() -> bytes:
    """Create a test document image as bytes."""
    img = Image.new("RGB", (800, 600), (255, 255, 255))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.text((100, 100), "Benchmark test document", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def run_single_request(client, url: str, image_bytes: bytes) -> float:
    """Send one request and return latency in ms."""
    start = time.time()
    try:
        response = await client.post(
            f"{url}/predict/v1",
            files={"file": ("test.png", image_bytes, "image/png")},
            data={"doc_type": "aadhaar"},
        )
        latency = (time.time() - start) * 1000
        return latency
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return -1


async def benchmark_sequential(url: str, n: int = 100) -> list[float]:
    """Run N sequential requests."""
    import httpx
    image_bytes = create_test_image()
    latencies = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(n):
            lat = await run_single_request(client, url, image_bytes)
            if lat > 0:
                latencies.append(lat)
    return latencies


async def benchmark_concurrent(url: str, n: int = 100) -> list[float]:
    """Run N concurrent requests."""
    import httpx
    image_bytes = create_test_image()
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = [run_single_request(client, url, image_bytes) for _ in range(n)]
        latencies = await asyncio.gather(*tasks)
    return [l for l in latencies if l > 0]


def compute_percentiles(latencies: list[float]) -> dict:
    """Compute p50, p95, p99 latency statistics."""
    if not latencies:
        return {"p50": 0, "p95": 0, "p99": 0, "mean": 0, "count": 0}
    arr = np.array(latencies)
    return {
        "p50": round(float(np.percentile(arr, 50)), 2),
        "p95": round(float(np.percentile(arr, 95)), 2),
        "p99": round(float(np.percentile(arr, 99)), 2),
        "mean": round(float(arr.mean()), 2),
        "min": round(float(arr.min()), 2),
        "max": round(float(arr.max()), 2),
        "count": len(latencies),
    }


async def run_benchmark(url: str = "http://localhost:8001"):
    """Run full benchmark suite."""
    print(f"\n{'='*60}")
    print(f"BharatDoc-VLM Inference Benchmark")
    print(f"Target: {url}")
    print(f"{'='*60}")

    # Sequential
    print(f"\n📊 Sequential (100 requests)...")
    seq_start = time.time()
    seq_latencies = await benchmark_sequential(url, 100)
    seq_time = time.time() - seq_start
    seq_stats = compute_percentiles(seq_latencies)
    seq_rps = len(seq_latencies) / seq_time if seq_time > 0 else 0

    print(f"  p50: {seq_stats['p50']}ms | p95: {seq_stats['p95']}ms | p99: {seq_stats['p99']}ms")
    print(f"  Throughput: {seq_rps:.1f} req/s")

    # Concurrent
    print(f"\n📊 Concurrent (100 requests)...")
    conc_start = time.time()
    conc_latencies = await benchmark_concurrent(url, 100)
    conc_time = time.time() - conc_start
    conc_stats = compute_percentiles(conc_latencies)
    conc_rps = len(conc_latencies) / conc_time if conc_time > 0 else 0

    print(f"  p50: {conc_stats['p50']}ms | p95: {conc_stats['p95']}ms | p99: {conc_stats['p99']}ms")
    print(f"  Throughput: {conc_rps:.1f} req/s")

    print(f"\n{'='*60}")
    return {"sequential": seq_stats, "concurrent": conc_stats,
            "sequential_rps": round(seq_rps, 1), "concurrent_rps": round(conc_rps, 1)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8001")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_benchmark(args.url))
