"""
GPU-Accelerated Magic Square of Squares Solver — v3 (Phase 26 Optimization)
"The Ghost of the Center"

Pipeline:
  1. GPU Phase (The Sluice Box): Filter combinations from itertools.combinations
     using PERMUTATION-INVARIANT set-level checks:
     - sum(combo) % 3 == 0 (Magic Constant M must be integer)
     - M must be present in the 9-number set (Center Check)
     - Range bounds
     Eliminates ~90% of combinations in milliseconds.

  2. CPU Phase (The Panners): Each survivor is passed to magic.check_magic(), 
     which handles internal permutations (8! = 40,320 per center choice)
     and full geometric validation.

This v3 optimization fixes the v2 CPU bottleneck by ensuring the CPU only 
sees combinations that have a mathematically valid center element.
"""

import sys
import time
import itertools
import multiprocessing as mp
import json
from pathlib import Path
from collections import deque

# Add local module paths
BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

import magic
import gpu_magic_filter

STATE_FILE = BASE / "hunting_magic_state.json"
GPU_BATCH_SIZE = 1_000_000  # 1M is more stable for VRAM and RAM overhead

def load_state():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                s = json.load(f)
                return s.get("chunks_processed", 0), s.get("total_found", 0)
        except Exception:
            pass
    return 0, 0

def save_state(chunks_processed, total_found):
    with open(STATE_FILE, "w") as f:
        json.dump({
            "chunks_processed": chunks_processed,
            "total_found": total_found,
            "timestamp": time.time()
        }, f, indent=4)


def validate_combination(combo_tuple):
    """
    CPU Worker: Receives a flat sorted combination of 9 perfect squares.
    """
    return magic.check_magic(list(combo_tuple), target_center=None, delta_tol=18, phi_tol=0.05)


def run_solver(cores=16):
    print("\n========================================================")
    print("  GPU-ACCELERATED MAGIC SQUARES SOLVER (v3 — Optimized)")
    print("  Pipeline: GPU Combination Filter → CPU Permutation Check")
    print("========================================================\n")

    combos = itertools.combinations(magic.numbers, 9)
    chunks_processed, total_found = load_state()
    items_to_skip = chunks_processed * GPU_BATCH_SIZE

    if items_to_skip > 0:
        print(f"[SOLVER] Resuming from state: skipping {items_to_skip:,} combinations...")
        deque(itertools.islice(combos, items_to_skip), maxlen=0)
        print("[SOLVER] Generator restored.\n")
    else:
        print(f"[SOLVER] Starting fresh. Number pool: {len(magic.numbers)} perfect squares")
        print(f"[SOLVER] Total search space: C({len(magic.numbers)},9) ≈ 2.3 billion combinations\n")

    print(f"[SOLVER] GPU batch size : {GPU_BATCH_SIZE:,} combinations")
    print(f"[SOLVER] CPU workers    : {cores} threads\n")
    time.sleep(1)

    with mp.Pool(cores) as pool:
        while True:
            # === PHASE A: GPU COMBINATION PRE-FILTER ===
            chunk = list(itertools.islice(combos, GPU_BATCH_SIZE))
            if not chunk:
                print("\n[!!!] SEARCH COMPLETE. All combinations evaluated.")
                break

            batch_idx = chunks_processed * GPU_BATCH_SIZE
            print(f"[{time.strftime('%H:%M:%S')}] Batch {chunks_processed+1} | Start: {batch_idx:,}")

            t0 = time.time()
            gpu_survivors = gpu_magic_filter.filter_combinations_gpu(chunk)
            gpu_ms = (time.time() - t0) * 1000
            survivor_count = len(gpu_survivors)
            pct = 100.0 * (1 - survivor_count / len(chunk))
            print(f"   [GPU] {len(chunk):,} → {survivor_count:,} set-survivors in {gpu_ms:.0f}ms ({pct:.2f}% eliminated)")

            # === PHASE B: CPU PERMUTATION + VALIDATION ===
            if survivor_count > 0:
                t1 = time.time()
                cs = max(1, survivor_count // cores)
                results = list(pool.imap_unordered(validate_combination, gpu_survivors, chunksize=cs))
                cpu_ms = (time.time() - t1) * 1000

                hits = [r for r in results if r is not None]
                print(f"   [CPU] {survivor_count:,} candidates validated in {cpu_ms:.0f}ms | Hits: {len(hits)}")

                for grid in hits:
                    total_found += 1
                    print("\n" + "=" * 50)
                    print(f"  *** MAGIC SQUARE OF SQUARES FOUND (#{total_found}) ***")
                    print("=" * 50)
                    magic.print_magic_square(grid)
                    magic.export_grid(grid, filename=str(BASE / "found_squares.txt"))

            chunks_processed += 1
            save_state(chunks_processed, total_found)


if __name__ == "__main__":
    mp.freeze_support()
    run_solver(cores=16)
